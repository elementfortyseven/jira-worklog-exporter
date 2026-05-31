"""Background worker: search for Jira users by query string."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QObject, Signal, Slot

from jwe.api.user import User


class UserSearchWorker(QObject):
    """Persistent worker; lives on its own thread for widget lifetime.

    Queries arrive via query_requested signal (queued connection).
    Results emitted via results / failed signals.
    """

    results = Signal(list)          # list[User]
    failed = Signal(str)            # error message

    query_requested = Signal(str)   # query string

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._search_fn: Callable[[str], list[User]] | None = None
        self.query_requested.connect(self._on_query_requested)

    def set_search_fn(self, fn: Callable[[str], list[User]] | None) -> None:
        """Called from main thread. Atomic attribute assignment (GIL)."""
        self._search_fn = fn

    @Slot(str)
    def _on_query_requested(self, query: str) -> None:
        """Runs on worker thread."""
        fn = self._search_fn  # snapshot
        if fn is None:
            self.failed.emit("Authentication required")
            return
        try:
            users = fn(query)
            self.results.emit(users)
        except Exception as exc:
            self.failed.emit(str(exc))
