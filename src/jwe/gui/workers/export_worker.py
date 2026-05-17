"""Background worker: consume run_export generator and emit progress signals."""

from __future__ import annotations

import threading
from collections.abc import Callable, Iterator

from PySide6.QtCore import QObject, Signal

from jwe.config import ExportConfig
from jwe.exporter import ExportProgress, ExportResult


class ExportWorker(QObject):
    """Worker that consumes the run_export generator and emits progress signals.

    Unlike one-shot workers (ConnectionTestWorker, UserSearchWorker), this worker
    consumes an iterator that yields multiple ExportProgress events before a
    terminal ExportResult.
    """

    progress_updated = Signal(int, int)  # issues_seen, worklogs_written
    log_message = Signal(str)            # human-readable status line
    finished = Signal(str)               # output_path (empty string for dry_run)
    failed = Signal(str)                 # user-facing error message

    def __init__(
        self,
        config: ExportConfig,
        run_fn: Callable[
            [ExportConfig, threading.Event],
            Iterator[ExportProgress | ExportResult],
        ],
        cancel_event: threading.Event,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._config = config
        self._run_fn = run_fn
        self._cancel_event = cancel_event

    def run(self) -> None:
        """Consume the generator; emit progress_updated, log_message, finished, or failed."""
        try:
            for event in self._run_fn(self._config, self._cancel_event):
                if isinstance(event, ExportProgress):
                    self.progress_updated.emit(event.issues_seen, event.worklogs_written)
                    if event.message:
                        # TODO etappe 6: localize ExportProgress.message via key-mapping in log_message slot
                        self.log_message.emit(event.message)
                elif isinstance(event, ExportResult):
                    self.finished.emit(event.output_path or "")
        except Exception as exc:
            self.failed.emit(str(exc))
