"""Streaming CSV writer for the worklog export.

The writer is a context manager that opens the output file with
``utf-8-sig`` encoding (UTF-8 with BOM, required for German Excel to handle
umlauts correctly), writes the header on entry, and exposes
:meth:`append_row` for each worklog. **The writer flushes after every row**
so very large exports don't accumulate in memory.
"""

from __future__ import annotations

import csv
from collections.abc import Callable
from pathlib import Path
from types import TracebackType
from typing import Any, TextIO

from jwe.adf import adf_to_text
from jwe.api.search import IssueRef
from jwe.api.worklog import Worklog
from jwe.config import ColumnProfile

# Each column is (header_name, row_value_extractor).
# Header and value stay co-located so they can never drift apart.
_Col = tuple[str, Callable[[IssueRef, Worklog], object]]

_MINIMAL_COLUMNS: list[_Col] = [
    ("project_key",                lambda i, w: i.project_key),
    ("issue_key",                  lambda i, w: w.issue_key),
    ("issue_summary",              lambda i, w: i.summary),
    ("worklog_author_displayname", lambda i, w: w.author_display_name),
    ("time_spent",                 lambda i, w: w.time_spent),
    ("work_description",           lambda i, w: adf_to_text(w.comment_adf) if w.comment_adf is not None else ""),
]

_STANDARD_EXTRA: list[_Col] = [
    ("project_name",              lambda i, w: i.project_name),
    ("worklog_author_email",      lambda i, w: w.author_email),
    ("worklog_started",           lambda i, w: w.started),
    ("time_spent_seconds",        lambda i, w: w.time_spent_seconds),
]

_FULL_EXTRA: list[_Col] = [
    ("worklog_author_account_id", lambda i, w: w.author_account_id),
    ("worklog_id",                lambda i, w: w.id),
    ("worklog_created",           lambda i, w: w.created),
    ("worklog_updated",           lambda i, w: w.updated),
]

_COLUMNS_BY_PROFILE: dict[ColumnProfile, list[_Col]] = {
    ColumnProfile.MINIMAL:  _MINIMAL_COLUMNS,
    ColumnProfile.STANDARD: _MINIMAL_COLUMNS + _STANDARD_EXTRA,
    ColumnProfile.FULL:     _MINIMAL_COLUMNS + _STANDARD_EXTRA + _FULL_EXTRA,
}


class WorklogCsvWriter:
    """Streaming CSV writer scoped to a single output file."""

    def __init__(
        self,
        path: Path,
        *,
        column_profile: ColumnProfile = ColumnProfile.STANDARD,
        delimiter: str = ",",
    ) -> None:
        self.path = path
        self.column_profile = column_profile
        self.delimiter = delimiter
        self._file: TextIO | None = None
        self._writer: Any = None  # csv._writer; private type avoided intentionally

    def __enter__(self) -> WorklogCsvWriter:
        self._file = self.path.open("w", encoding="utf-8-sig", newline="")
        self._writer = csv.writer(self._file, delimiter=self.delimiter, quoting=csv.QUOTE_MINIMAL)
        columns = _COLUMNS_BY_PROFILE[self.column_profile]
        self._writer.writerow([name for name, _ in columns])
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        if self._file is not None:
            self._file.close()

    def append_row(self, issue: IssueRef, worklog: Worklog) -> None:
        """Append one row to the CSV and flush immediately."""
        assert self._file is not None and self._writer is not None, (
            "append_row called outside of context manager"
        )
        columns = _COLUMNS_BY_PROFILE[self.column_profile]
        self._writer.writerow([extractor(issue, worklog) for _, extractor in columns])
        self._file.flush()
