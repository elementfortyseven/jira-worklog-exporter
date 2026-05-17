"""Background worker: search for Jira users by query string."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QObject, Signal

from jwe.api.user import User


class UserSearchWorker(QObject):
    """One-shot worker that calls search_fn and emits results or failed."""

    results = Signal(list)  # list[User]
    failed = Signal(str)    # user-facing error message

    def __init__(
        self,
        query: str,
        search_fn: Callable[[str], list[User]],
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._query = query
        self._search_fn = search_fn

    def run(self) -> None:
        """Call search_fn; always emits results or failed."""
        try:
            users = self._search_fn(self._query)
            self.results.emit(users)
        except Exception as exc:
            self.failed.emit(str(exc))
