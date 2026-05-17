"""Background worker: discover Jira Cloud ID from a site URL."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QObject, Signal

from jwe.api.tenant_info import TenantInfo


class CloudIdDiscoverWorker(QObject):
    """One-shot worker that calls discover_fn and emits discovered or failed."""

    discovered = Signal(str)  # cloud_id
    failed = Signal(str)      # user-facing error message

    def __init__(
        self,
        site_url: str,
        discover_fn: Callable[[str], TenantInfo],
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._site_url = site_url
        self._discover_fn = discover_fn

    def run(self) -> None:
        """Call discover_fn; always emits discovered or failed."""
        try:
            info = self._discover_fn(self._site_url)
            self.discovered.emit(info.cloud_id)
        except Exception as exc:
            self.failed.emit(str(exc))
