"""Background worker: verify Jira connectivity."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QObject, Signal

from jwe.api.client import AuthenticationError, JiraPermissionError
from jwe.api.user import User
from jwe.config import ExportConfig


class ConnectionTestWorker(QObject):
    """One-shot worker that calls test_fn and emits finished or failed."""

    finished = Signal(str, str)  # display_name, email
    failed = Signal(str)         # user-facing error message

    def __init__(
        self,
        config: ExportConfig,
        test_fn: Callable[[ExportConfig], User],
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._config = config
        self._test_fn = test_fn

    def run(self) -> None:
        """Call test_fn; always emits finished or failed."""
        try:
            user = self._test_fn(self._config)
            self.finished.emit(user.display_name, user.email)
        except AuthenticationError:
            self.failed.emit(
                "Authentication failed: invalid token or missing scopes. "
                "For Service Accounts, verify all required scopes are selected."
            )
        except JiraPermissionError:
            self.failed.emit(
                "Permission denied: account lacks required permissions. "
                "Check project membership and token scopes."
            )
        except Exception as exc:
            self.failed.emit(str(exc))
