"""Domain orchestration: tie API client, search, worklog fetch, and CSV
writer into one export run.

This module is the only one that needs to know about the full pipeline.
:func:`run_export` is what both the CLI and the GUI call.
"""

from __future__ import annotations

import contextlib
import logging
import threading
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from jwe.api.client import JiraCloudClient
from jwe.api.search import build_jql, iter_issues
from jwe.api.worklog import iter_worklogs
from jwe.config import ExportConfig
from jwe.csv_writer import WorklogCsvWriter

logger = logging.getLogger(__name__)

_PROGRESS_EVERY_N_ISSUES = 10
_PROGRESS_EVERY_N_WORKLOGS = 50


@dataclass(frozen=True)
class ExportProgress:
    """A progress event emitted during an export run.

    Attributes:
        issues_seen: Cumulative count of issues fetched from JQL search.
        worklogs_written: Cumulative count of worklogs written to CSV.
        message: Optional human-readable status line.
    """

    issues_seen: int
    worklogs_written: int
    message: str = ""


@dataclass(frozen=True)
class ExportResult:
    """Final outcome of an export run.

    Attributes:
        issues_seen: Total issues considered.
        worklogs_written: Total worklogs written (or counted in dry-run mode).
        total_time_spent_seconds: Sum of ``time_spent_seconds`` across
            worklogs — useful for sanity-checking against expected staff hours.
        output_path: Path to the CSV, or ``None`` in dry-run mode.
    """

    issues_seen: int
    worklogs_written: int
    total_time_spent_seconds: int
    output_path: str | None


def _make_output_path(config: ExportConfig) -> Path:
    assert config.from_date is not None
    assert config.to_date is not None
    timestamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    filename = (
        f"jira_worklogs_{config.from_date.isoformat()}"
        f"_{config.to_date.isoformat()}_{timestamp}.csv"
    )
    return config.output_dir / filename


def run_export(
    config: ExportConfig,
    cancel_event: threading.Event | None = None,
) -> Iterator[ExportProgress | ExportResult]:
    """Run an export, yielding progress events and a final :class:`ExportResult`.

    Args:
        config: Validated configuration.
        cancel_event: Optional cancellation flag. When set, the run stops
            cleanly between issues and yields a final result with the partial
            counts.

    Yields:
        Zero or more :class:`ExportProgress` events, followed by exactly one
        terminal :class:`ExportResult`.
    """
    config.validate()
    logger.info("Starting export: %s", config.to_redacted_dict())

    auth = config.build_auth()
    assert config.from_date is not None
    assert config.to_date is not None

    jql = build_jql(
        config.user_account_ids,
        config.from_date,
        config.to_date,
        config.project_keys or None,
    )

    issues_seen = 0
    worklogs_written = 0
    total_time_spent_seconds = 0
    output_path: Path | None = None

    last_progress_issues = 0
    last_progress_worklogs = 0

    account_ids_set = set(config.user_account_ids)

    with contextlib.ExitStack() as stack:
        client = stack.enter_context(JiraCloudClient.from_auth(auth))
        client.connect()

        writer: WorklogCsvWriter | None = None
        if not config.dry_run:
            output_path = _make_output_path(config)
            writer = stack.enter_context(
                WorklogCsvWriter(
                    output_path,
                    column_profile=config.column_profile,
                    delimiter=config.delimiter,
                )
            )

        for issue in iter_issues(client, jql):
            if cancel_event is not None and cancel_event.is_set():
                break

            issues_seen += 1
            logger.debug("Processing issue %s", issue.key)

            for worklog in iter_worklogs(
                client,
                issue.key,
                config.from_date,
                config.to_date,
                account_ids_set,
            ):
                if writer is not None:
                    writer.append_row(issue, worklog)
                worklogs_written += 1
                total_time_spent_seconds += worklog.time_spent_seconds

                if worklogs_written - last_progress_worklogs >= _PROGRESS_EVERY_N_WORKLOGS:
                    last_progress_worklogs = worklogs_written
                    last_progress_issues = issues_seen
                    yield ExportProgress(
                        issues_seen=issues_seen,
                        worklogs_written=worklogs_written,
                    )

            if issues_seen - last_progress_issues >= _PROGRESS_EVERY_N_ISSUES:
                last_progress_issues = issues_seen
                yield ExportProgress(
                    issues_seen=issues_seen,
                    worklogs_written=worklogs_written,
                )

    if cancel_event is not None and cancel_event.is_set():
        yield ExportProgress(
            issues_seen=issues_seen,
            worklogs_written=worklogs_written,
            message="Export cancelled.",  # i18n: exporter.msg.cancelled
        )
        return

    yield ExportProgress(
        issues_seen=issues_seen,
        worklogs_written=worklogs_written,
        message="Export complete.",  # i18n: exporter.msg.complete
    )
    yield ExportResult(
        issues_seen=issues_seen,
        worklogs_written=worklogs_written,
        total_time_spent_seconds=total_time_spent_seconds,
        output_path=str(output_path) if output_path is not None else None,
    )
