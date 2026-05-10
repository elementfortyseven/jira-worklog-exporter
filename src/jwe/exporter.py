"""Domain orchestration: tie API client, search, worklog fetch, and CSV
writer into one export run.

This module is the only one that needs to know about the full pipeline.
:func:`run_export` is what both the CLI and the GUI call.

TODO (claude code):
1. Implement :func:`run_export` per the data flow in CLAUDE.md §4.
2. Yield progress events (issues counted, worklogs written) so the CLI's
   tqdm bar and the GUI's progressbar can stay live without coupling.
3. In ``--dry-run`` mode, count but do not write.
4. Cancellation: accept a ``cancel_event: threading.Event``; check it
   between issues. The GUI passes one in; the CLI plumbs Ctrl-C through.
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Iterator
from dataclasses import dataclass

from jwe.config import ExportConfig

logger = logging.getLogger(__name__)


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
        worklogs_written: Total worklogs written (0 in ``--dry-run``).
        total_time_spent_seconds: Sum of ``time_spent_seconds`` across
            written worklogs — useful for sanity-checking against expected
            staff hours.
        output_path: Path to the CSV (or ``None`` for ``--dry-run``).
    """

    issues_seen: int
    worklogs_written: int
    total_time_spent_seconds: int
    output_path: str | None


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

    TODO: implement. See CLAUDE.md §4 and §7 step 9.
    """
    raise NotImplementedError("Implement run_export — see CLAUDE.md §7 step 9")
    yield  # pragma: no cover
