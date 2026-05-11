"""Tests for jwe.exporter."""

from __future__ import annotations

import json
import re
import threading
from datetime import date
from pathlib import Path
from typing import Any

import pytest
import responses

from jwe.api.auth import AuthMode
from jwe.api.client import AuthenticationError
from jwe.config import ExportConfig
from jwe.exporter import ExportProgress, ExportResult, run_export

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_CLOUD_ID = "1a11d016-8984-4c3e-b9ab-142dd06acb1b"
_SA_BASE = f"https://api.atlassian.com/ex/jira/{_CLOUD_ID}"
_MYSELF_URL = f"{_SA_BASE}/rest/api/3/myself"
_SEARCH_URL = f"{_SA_BASE}/rest/api/3/search/jql"

_SA_EMAIL = "jwe-bot@serviceaccount.atlassian.com"
_SA_TOKEN = "ATATT3xFfGF0dummy_service_account_token_value"
_ACCOUNT_IDS = ["user-001", "user-002"]
_FROM = date(2026, 4, 1)
_TO = date(2026, 4, 30)

_MYSELF: dict[str, object] = {
    "accountId": "5b10ac8d82e05b22cc7d4ef5",
    "displayName": "Jira Bot",
    "emailAddress": _SA_EMAIL,
    "active": True,
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _issue(key: str, project_key: str = "PROJ") -> dict[str, Any]:
    return {
        "key": key,
        "fields": {
            "summary": f"Summary of {key}",
            "project": {"key": project_key, "name": f"Project {project_key}"},
        },
    }


def _wl(wl_id: str, account_id: str = "user-001") -> dict[str, Any]:
    return {
        "id": wl_id,
        "author": {
            "accountId": account_id,
            "displayName": f"User {account_id}",
            "emailAddress": f"{account_id}@example.com",
        },
        "started": "2026-04-15T10:00:00.000+0000",
        "timeSpent": "1h",
        "timeSpentSeconds": 3600,
        "created": "2026-04-15T10:05:00.000+0000",
        "updated": "2026-04-15T10:05:00.000+0000",
    }


def _search_page(issues: list[dict[str, Any]]) -> dict[str, Any]:
    return {"issues": issues}


def _worklog_page(worklogs: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "worklogs": worklogs,
        "startAt": 0,
        "maxResults": 1000,
        "total": len(worklogs),
    }


def _worklog_url(issue_key: str) -> str:
    return f"{_SA_BASE}/rest/api/3/issue/{issue_key}/worklog"


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def base_config(tmp_path: Path) -> ExportConfig:
    return ExportConfig(
        auth_mode=AuthMode.SERVICE_ACCOUNT,
        cloud_id=_CLOUD_ID,
        service_account_email=_SA_EMAIL,
        api_token=_SA_TOKEN,
        user_account_ids=list(_ACCOUNT_IDS),
        from_date=_FROM,
        to_date=_TO,
        output_dir=tmp_path,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestRunExport:
    @responses.activate
    def test_happy_path_two_issues_four_worklogs(
        self, base_config: ExportConfig, tmp_path: Path
    ) -> None:
        """Happy path: 2 issues x 2 worklogs -> 4 CSV rows, correct counts."""
        responses.add(responses.GET, _MYSELF_URL, json=_MYSELF)
        responses.add(
            responses.POST,
            _SEARCH_URL,
            json=_search_page([_issue("PROJ-1"), _issue("PROJ-2")]),
        )
        responses.add(
            responses.GET,
            _worklog_url("PROJ-1"),
            json=_worklog_page([_wl("1001"), _wl("1002")]),
        )
        responses.add(
            responses.GET,
            _worklog_url("PROJ-2"),
            json=_worklog_page([_wl("2001"), _wl("2002")]),
        )

        events = list(run_export(base_config))

        result = next(e for e in events if isinstance(e, ExportResult))
        assert result.issues_seen == 2
        assert result.worklogs_written == 4
        assert result.total_time_spent_seconds == 4 * 3600
        assert result.output_path is not None

        csv_path = Path(result.output_path)
        assert csv_path.exists()
        lines = csv_path.read_text(encoding="utf-8-sig").splitlines()
        assert len(lines) == 5  # 1 header + 4 data rows

    @responses.activate
    def test_dry_run_writes_no_file(
        self, base_config: ExportConfig, tmp_path: Path
    ) -> None:
        """In dry-run mode no CSV is created; counts still reflect what was processed."""
        base_config.dry_run = True
        responses.add(responses.GET, _MYSELF_URL, json=_MYSELF)
        responses.add(
            responses.POST,
            _SEARCH_URL,
            json=_search_page([_issue("PROJ-1")]),
        )
        responses.add(
            responses.GET,
            _worklog_url("PROJ-1"),
            json=_worklog_page([_wl("1001"), _wl("1002")]),
        )

        events = list(run_export(base_config))

        result = next(e for e in events if isinstance(e, ExportResult))
        assert result.output_path is None
        assert result.issues_seen == 1
        assert result.worklogs_written == 2
        assert not list(tmp_path.glob("*.csv"))

    @responses.activate
    def test_cancel_before_first_issue_yields_zero_counts(
        self, base_config: ExportConfig
    ) -> None:
        """Cancel already set → loop breaks before any issue is processed."""
        cancel = threading.Event()
        cancel.set()

        responses.add(responses.GET, _MYSELF_URL, json=_MYSELF)
        # Search is called once to start iteration, but no worklog calls follow.
        responses.add(
            responses.POST,
            _SEARCH_URL,
            json=_search_page([_issue("PROJ-1"), _issue("PROJ-2")]),
        )

        events = list(run_export(base_config, cancel_event=cancel))

        result = next(e for e in events if isinstance(e, ExportResult))
        assert result.issues_seen == 0
        assert result.worklogs_written == 0

    @responses.activate
    def test_cancel_after_first_issue_yields_partial_counts(
        self, base_config: ExportConfig, tmp_path: Path
    ) -> None:
        """Cancel set during PROJ-1 worklog fetch → only PROJ-1's rows in CSV."""
        cancel = threading.Event()

        responses.add(responses.GET, _MYSELF_URL, json=_MYSELF)
        responses.add(
            responses.POST,
            _SEARCH_URL,
            json=_search_page([_issue("PROJ-1"), _issue("PROJ-2")]),
        )

        def _worklog_and_cancel(
            req: Any,
        ) -> tuple[int, dict[str, str], str]:
            cancel.set()
            return (
                200,
                {"Content-Type": "application/json"},
                json.dumps(_worklog_page([_wl("1001")])),
            )

        responses.add_callback(
            responses.GET,
            _worklog_url("PROJ-1"),
            callback=_worklog_and_cancel,
        )

        events = list(run_export(base_config, cancel_event=cancel))

        result = next(e for e in events if isinstance(e, ExportResult))
        assert result.issues_seen == 1
        assert result.worklogs_written == 1
        assert result.output_path is not None
        lines = Path(result.output_path).read_text(encoding="utf-8-sig").splitlines()
        assert len(lines) == 2  # 1 header + 1 data row

    @responses.activate
    def test_foreign_account_id_not_written(
        self, base_config: ExportConfig, tmp_path: Path
    ) -> None:
        """Worklogs from account IDs not in user_account_ids are filtered out."""
        responses.add(responses.GET, _MYSELF_URL, json=_MYSELF)
        responses.add(
            responses.POST,
            _SEARCH_URL,
            json=_search_page([_issue("PROJ-1")]),
        )
        responses.add(
            responses.GET,
            _worklog_url("PROJ-1"),
            json=_worklog_page([_wl("1001", "user-001"), _wl("1002", "FOREIGN-999")]),
        )

        events = list(run_export(base_config))

        result = next(e for e in events if isinstance(e, ExportResult))
        assert result.worklogs_written == 1
        assert result.output_path is not None
        lines = Path(result.output_path).read_text(encoding="utf-8-sig").splitlines()
        assert len(lines) == 2  # 1 header + 1 data row

    @responses.activate
    def test_authentication_error_propagates_no_csv_created(
        self, base_config: ExportConfig, tmp_path: Path
    ) -> None:
        """AuthenticationError from connect() propagates; no CSV file is created."""
        responses.add(
            responses.GET,
            _MYSELF_URL,
            status=401,
            json={"errorMessages": ["Unauthorized"]},
        )

        with pytest.raises(AuthenticationError):
            list(run_export(base_config))

        assert not list(tmp_path.glob("*.csv"))

    @responses.activate
    def test_output_filename_matches_pattern(
        self, base_config: ExportConfig
    ) -> None:
        """CSV filename follows jira_worklogs_<from>_<to>_<timestamp>.csv pattern."""
        responses.add(responses.GET, _MYSELF_URL, json=_MYSELF)
        responses.add(responses.POST, _SEARCH_URL, json=_search_page([]))

        events = list(run_export(base_config))
        result = next(e for e in events if isinstance(e, ExportResult))

        assert result.output_path is not None
        filename = Path(result.output_path).name
        assert re.match(
            r"jira_worklogs_2026-04-01_2026-04-30_\d{8}T\d{6}\.csv", filename
        )

    @responses.activate
    def test_progress_events_yielded_before_result(
        self, base_config: ExportConfig
    ) -> None:
        """At least one ExportProgress event is yielded; ExportResult is last."""
        responses.add(responses.GET, _MYSELF_URL, json=_MYSELF)
        responses.add(
            responses.POST,
            _SEARCH_URL,
            json=_search_page([_issue("PROJ-1")]),
        )
        responses.add(
            responses.GET,
            _worklog_url("PROJ-1"),
            json=_worklog_page([_wl("1001")]),
        )

        events = list(run_export(base_config))

        progress_events = [e for e in events if isinstance(e, ExportProgress)]
        assert len(progress_events) >= 1
        assert isinstance(events[-1], ExportResult)
        assert isinstance(events[-2], ExportProgress)
