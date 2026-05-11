"""Tests for jwe.csv_writer.WorklogCsvWriter."""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from jwe.api.search import IssueRef
from jwe.api.worklog import Worklog
from jwe.config import ColumnProfile
from jwe.csv_writer import WorklogCsvWriter

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

_ISSUE = IssueRef(
    key="PROJ-42",
    summary="Implement login",
    project_key="PROJ",
    project_name="Project Alpha",
)

_PLAIN_ADF = {
    "type": "doc",
    "version": 1,
    "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Fixed the bug"}]}],
}

_WORKLOG = Worklog(
    id="10001",
    issue_key="PROJ-42",
    author_account_id="5b10a2844c20165700ede21g",
    author_display_name="Martin Hilbig",
    author_email="martin@example.com",
    started="2026-04-15T09:00:00.000+0000",
    time_spent="2h",
    time_spent_seconds=7200,
    comment_adf=_PLAIN_ADF,
    created="2026-04-15T09:05:00.000+0000",
    updated="2026-04-15T09:05:00.000+0000",
)

_WORKLOG_NO_COMMENT = Worklog(
    id="10002",
    issue_key="PROJ-42",
    author_account_id="5b10a2844c20165700ede21g",
    author_display_name="Martin Hilbig",
    author_email="martin@example.com",
    started="2026-04-15T10:00:00.000+0000",
    time_spent="1h",
    time_spent_seconds=3600,
    comment_adf=None,
    created="2026-04-15T10:05:00.000+0000",
    updated="2026-04-15T10:05:00.000+0000",
)


# ---------------------------------------------------------------------------
# Context-manager behaviour
# ---------------------------------------------------------------------------

class TestContextManager:
    def test_enter_opens_file(self, tmp_path: Path) -> None:
        p = tmp_path / "out.csv"
        with WorklogCsvWriter(p) as w:
            assert w._file is not None
            assert not w._file.closed

    def test_exit_closes_file(self, tmp_path: Path) -> None:
        p = tmp_path / "out.csv"
        with WorklogCsvWriter(p) as w:
            file_ref = w._file
        assert file_ref is not None
        assert file_ref.closed

    def test_exit_propagates_exception(self, tmp_path: Path) -> None:
        p = tmp_path / "out.csv"
        with pytest.raises(RuntimeError, match="boom"), WorklogCsvWriter(p):
            raise RuntimeError("boom")


# ---------------------------------------------------------------------------
# Encoding
# ---------------------------------------------------------------------------

class TestEncoding:
    def test_utf8_bom_present(self, tmp_path: Path) -> None:
        p = tmp_path / "out.csv"
        with WorklogCsvWriter(p):
            pass
        assert p.read_bytes()[:3] == b"\xef\xbb\xbf"

    def test_umlaut_roundtrips_correctly(self, tmp_path: Path) -> None:
        umlaut_issue = IssueRef(
            key="PROJ-99",
            summary="Refactoring der Anmeldung",
            project_key="PROJ",
            project_name="Projekt Übergabe",
        )
        p = tmp_path / "out.csv"
        with WorklogCsvWriter(p, column_profile=ColumnProfile.STANDARD) as w:
            w.append_row(umlaut_issue, _WORKLOG_NO_COMMENT)
        raw = p.read_bytes()
        assert b"Refactoring der Anmeldung" in raw
        assert "Projekt Übergabe".encode() in raw


# ---------------------------------------------------------------------------
# Header rows
# ---------------------------------------------------------------------------

class TestHeaders:
    def _headers(self, tmp_path: Path, profile: ColumnProfile) -> list[str]:
        p = tmp_path / "out.csv"
        with WorklogCsvWriter(p, column_profile=profile):
            pass
        with p.open(encoding="utf-8-sig") as f:
            return next(csv.reader(f))

    def test_minimal_has_six_columns(self, tmp_path: Path) -> None:
        headers = self._headers(tmp_path, ColumnProfile.MINIMAL)
        assert len(headers) == 6
        assert headers == [
            "project_key", "issue_key", "issue_summary",
            "worklog_author_displayname", "time_spent", "work_description",
        ]

    def test_standard_has_ten_columns(self, tmp_path: Path) -> None:
        headers = self._headers(tmp_path, ColumnProfile.STANDARD)
        assert len(headers) == 10
        assert headers[:6] == [
            "project_key", "issue_key", "issue_summary",
            "worklog_author_displayname", "time_spent", "work_description",
        ]
        assert headers[6:] == [
            "project_name", "worklog_author_email",
            "worklog_started", "time_spent_seconds",
        ]

    def test_full_has_fourteen_columns(self, tmp_path: Path) -> None:
        headers = self._headers(tmp_path, ColumnProfile.FULL)
        assert len(headers) == 14
        assert headers[10:] == [
            "worklog_author_account_id", "worklog_id",
            "worklog_created", "worklog_updated",
        ]


# ---------------------------------------------------------------------------
# Data rows
# ---------------------------------------------------------------------------

class TestAppendRow:
    def _read_rows(self, path: Path) -> list[list[str]]:
        with path.open(encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            next(reader)  # skip header
            return list(reader)

    def test_standard_row_values(self, tmp_path: Path) -> None:
        p = tmp_path / "out.csv"
        with WorklogCsvWriter(p, column_profile=ColumnProfile.STANDARD) as w:
            w.append_row(_ISSUE, _WORKLOG)
        rows = self._read_rows(p)
        assert len(rows) == 1
        row = rows[0]
        assert row[0] == "PROJ"
        assert row[1] == "PROJ-42"
        assert row[2] == "Implement login"
        assert row[3] == "Martin Hilbig"
        assert row[4] == "2h"
        assert row[5] == "Fixed the bug"
        assert row[6] == "Project Alpha"
        assert row[7] == "martin@example.com"
        assert row[8] == "2026-04-15T09:00:00.000+0000"
        assert row[9] == "7200"

    def test_adf_comment_is_flattened(self, tmp_path: Path) -> None:
        p = tmp_path / "out.csv"
        with WorklogCsvWriter(p, column_profile=ColumnProfile.MINIMAL) as w:
            w.append_row(_ISSUE, _WORKLOG)
        rows = self._read_rows(p)
        assert rows[0][5] == "Fixed the bug"

    def test_none_comment_adf_produces_empty_string(self, tmp_path: Path) -> None:
        p = tmp_path / "out.csv"
        with WorklogCsvWriter(p, column_profile=ColumnProfile.MINIMAL) as w:
            w.append_row(_ISSUE, _WORKLOG_NO_COMMENT)
        rows = self._read_rows(p)
        assert rows[0][5] == ""

    def test_semicolon_delimiter_used(self, tmp_path: Path) -> None:
        p = tmp_path / "out.csv"
        with WorklogCsvWriter(p, column_profile=ColumnProfile.MINIMAL, delimiter=";") as w:
            w.append_row(_ISSUE, _WORKLOG_NO_COMMENT)
        raw = p.read_text(encoding="utf-8-sig")
        # Every row should be semicolon-separated, not comma-separated
        header_line = raw.splitlines()[0]
        assert ";" in header_line
        assert "," not in header_line

    def test_comma_in_summary_is_quoted(self, tmp_path: Path) -> None:
        issue_with_comma = IssueRef(
            key="PROJ-1",
            summary="Fix login, logout, and session",
            project_key="PROJ",
            project_name="Project Alpha",
        )
        p = tmp_path / "out.csv"
        with WorklogCsvWriter(p, column_profile=ColumnProfile.MINIMAL) as w:
            w.append_row(issue_with_comma, _WORKLOG_NO_COMMENT)
        rows = self._read_rows(p)
        assert rows[0][2] == "Fix login, logout, and session"

    def test_newline_in_description_is_handled(self, tmp_path: Path) -> None:
        multiline_adf = {
            "type": "doc",
            "version": 1,
            "content": [
                {"type": "paragraph", "content": [{"type": "text", "text": "Line one"}]},
                {"type": "paragraph", "content": [{"type": "text", "text": "Line two"}]},
            ],
        }
        worklog_multiline = Worklog(
            id="10003",
            issue_key="PROJ-42",
            author_account_id="aid1",
            author_display_name="Martin Hilbig",
            author_email="martin@example.com",
            started="2026-04-15T11:00:00.000+0000",
            time_spent="30m",
            time_spent_seconds=1800,
            comment_adf=multiline_adf,
            created="2026-04-15T11:05:00.000+0000",
            updated="2026-04-15T11:05:00.000+0000",
        )
        p = tmp_path / "out.csv"
        with WorklogCsvWriter(p, column_profile=ColumnProfile.MINIMAL) as w:
            w.append_row(_ISSUE, worklog_multiline)
        rows = self._read_rows(p)
        assert len(rows) == 1
        assert "Line one" in rows[0][5]
        assert "Line two" in rows[0][5]

    def test_flush_after_append_row(self, tmp_path: Path) -> None:
        p = tmp_path / "out.csv"
        with WorklogCsvWriter(p, column_profile=ColumnProfile.MINIMAL) as w:
            w.append_row(_ISSUE, _WORKLOG_NO_COMMENT)
            # Data must be on disk before __exit__ is called
            data = p.read_bytes()
        assert b"PROJ-42" in data
