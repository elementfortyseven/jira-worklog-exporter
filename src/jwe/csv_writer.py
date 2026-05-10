"""Streaming CSV writer for the worklog export.

The writer is a context manager that opens the output file with
``utf-8-sig`` encoding (UTF-8 with BOM, required for German Excel to handle
umlauts correctly), writes the header on entry, and exposes
:meth:`append_row` for each worklog. **The writer flushes after every row**
so very large exports don't accumulate in memory.

TODO (claude code):
1. Implement the context manager protocol.
2. Implement :meth:`append_row` mapping a :class:`Worklog` plus its parent
   :class:`IssueRef` to the requested column profile.
3. Use ``csv.QUOTE_MINIMAL``; let the ``csv`` module handle escaping.
4. The default delimiter is ``,``; users with German Excel should use ``;``.
5. ADF flattening of the comment happens here (call :func:`jwe.adf.adf_to_text`).
"""

from __future__ import annotations

from pathlib import Path
from types import TracebackType
from typing import TextIO

from jwe.api.search import IssueRef
from jwe.api.worklog import Worklog
from jwe.config import ColumnProfile


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

    def __enter__(self) -> WorklogCsvWriter:
        """Open the file, write header. TODO: implement."""
        raise NotImplementedError("Implement WorklogCsvWriter.__enter__")

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        """Close the file. TODO: implement."""
        raise NotImplementedError("Implement WorklogCsvWriter.__exit__")

    def append_row(self, issue: IssueRef, worklog: Worklog) -> None:
        """Append one row to the CSV and flush.

        TODO: implement. Map ``issue`` + ``worklog`` to the configured column
        profile. See PRD §8 and CLAUDE.md §6.
        """
        raise NotImplementedError("Implement WorklogCsvWriter.append_row")
