"""Background worker: consume run_export generator and emit progress signals."""

from __future__ import annotations

import threading
from collections.abc import Callable, Iterator

from PySide6.QtCore import QObject, Signal, Slot

from jwe.config import ExportConfig
from jwe.exporter import ExportProgress, ExportResult


class ExportWorker(QObject):
    """Worker that consumes the run_export generator and emits progress signals.

    Unlike one-shot workers (ConnectionTestWorker, UserSearchWorker), this worker
    lives for the lifetime of the application and accepts new export tasks via
    start_export().  The QThread event loop dispatches start_export as a queued
    slot, so the heavy work always runs off the main thread.
    """

    progress_updated = Signal(int, int)  # issues_seen, worklogs_written
    log_message = Signal(str)            # human-readable status line
    finished = Signal(str)               # output_path (empty string for dry_run)
    failed = Signal(str)                 # user-facing error message
    cancelled = Signal()                 # emitted when generator ended without result or error

    def __init__(
        self,
        run_fn: Callable[
            [ExportConfig, threading.Event],
            Iterator[ExportProgress | ExportResult],
        ],
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._run_fn = run_fn

    @Slot(object, object)
    def start_export(self, config: object, cancel_event: object) -> None:
        """Consume the run_export generator; emit progress, finished, failed, or cancelled."""
        if not isinstance(config, ExportConfig):
            raise TypeError(f"expected ExportConfig, got {type(config)!r}")
        if not isinstance(cancel_event, threading.Event):
            raise TypeError(f"expected threading.Event, got {type(cancel_event)!r}")
        _terminal_emitted = False
        try:
            for event in self._run_fn(config, cancel_event):
                if isinstance(event, ExportProgress):
                    self.progress_updated.emit(event.issues_seen, event.worklogs_written)
                elif isinstance(event, ExportResult):
                    self.finished.emit(event.output_path or "")
                    _terminal_emitted = True
        except Exception as exc:
            self.failed.emit(str(exc))
            _terminal_emitted = True
        if not _terminal_emitted:
            self.cancelled.emit()
