"""Main application window."""

from __future__ import annotations

import logging
import threading
from datetime import date
from pathlib import Path
from typing import Any, cast

from PySide6.QtCore import QByteArray, QSettings, Qt, QThread, QUrl, Signal
from PySide6.QtGui import QCloseEvent, QDesktopServices
from PySide6.QtWidgets import (
    QHBoxLayout,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

import jwe.service as _default_svc
from jwe.config import ColumnProfile, ExportConfig
from jwe.gui.widgets.auth import AuthWidget
from jwe.gui.widgets.filter import FilterWidget
from jwe.gui.widgets.output import OutputWidget
from jwe.gui.widgets.status import StatusWidget
from jwe.gui.widgets.user_search import UserSearchWidget
from jwe.gui.workers.export_worker import ExportWorker

logger = logging.getLogger(__name__)

_SETTINGS_ORG = "jira-worklog-exporter"
_SETTINGS_APP = "jwe-gui"


class MainWindow(QMainWindow):
    """Top-level application window; orchestrates all section widgets."""

    language_changed = Signal(str)

    def __init__(
        self,
        *,
        initial_lang: str | None = None,
        _settings: QSettings | None = None,
        service: Any = None,
    ) -> None:
        super().__init__()
        self._settings: QSettings = (
            _settings or QSettings(_SETTINGS_ORG, _SETTINGS_APP)
        )
        self._lang: str = "de"
        self._svc: Any = service if service is not None else _default_svc
        self._export_thread: QThread | None = None
        self._export_worker: ExportWorker | None = None
        self._cancel_event: threading.Event | None = None
        self._last_output_path: str | None = None

        self.auth_widget = AuthWidget(service=self._svc)
        self.user_search_widget = UserSearchWidget()
        self.filter_widget = FilterWidget()
        self.output_widget = OutputWidget()
        self.status_widget = StatusWidget()

        # Created here so mypy can see the type; placed in layout by _build_ui.
        self.lang_btn = QPushButton()
        self.lang_btn.setFlat(True)
        self.lang_btn.clicked.connect(self._toggle_language)

        self._build_ui()
        self._restore_settings(initial_lang)
        self._update_export_btn()
        self.status_widget.export_btn.clicked.connect(self._on_export_clicked)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        self.setWindowTitle("Jira Worklog Exporter")  # i18n: app.title
        self.setMinimumSize(800, 600)
        self.resize(960, 720)

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Header: language toggle button aligned right
        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(8, 4, 8, 4)
        header_layout.addStretch()
        header_layout.addWidget(self.lang_btn)
        root.addWidget(header)

        # Scroll area containing the four input sections
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(8, 8, 8, 8)
        content_layout.setSpacing(8)
        content_layout.addWidget(self.auth_widget)
        content_layout.addWidget(self.user_search_widget)
        content_layout.addWidget(self.filter_widget)
        content_layout.addWidget(self.output_widget)
        content_layout.addStretch()
        scroll.setWidget(content)
        root.addWidget(scroll, 1)

        # Status panel anchored at the bottom (outside the scroll area)
        root.addWidget(self.status_widget)

        # Validation wiring: any widget going valid/invalid refreshes the export button.
        self.auth_widget.validation_changed.connect(self._update_export_btn)
        self.user_search_widget.selection_changed.connect(self._update_export_btn)
        self.filter_widget.validation_changed.connect(self._update_export_btn)
        self.output_widget.validation_changed.connect(self._update_export_btn)

        # Connection-verify wiring: successful test enables user search;
        # any subsequent auth-field change clears it again.
        self.auth_widget.connection_verified.connect(self._on_connection_verified)
        self.auth_widget.connection_invalidated.connect(self._on_connection_invalidated)

        # Result buttons and cancel button wiring.
        self.status_widget.open_csv_btn.clicked.connect(self._on_open_csv_clicked)
        self.status_widget.open_folder_btn.clicked.connect(self._on_open_folder_clicked)
        self.status_widget.cancel_requested.connect(self._on_cancel_clicked)

    # ------------------------------------------------------------------
    # Settings persistence
    # ------------------------------------------------------------------

    def _restore_settings(self, initial_lang: str | None) -> None:
        saved_lang = cast(str, self._settings.value("lang", "de"))
        self._lang = initial_lang if initial_lang is not None else saved_lang
        self.lang_btn.setText(self._target_flag())
        geo_raw = self._settings.value("geometry", QByteArray())
        if isinstance(geo_raw, QByteArray) and not geo_raw.isEmpty():
            self.restoreGeometry(geo_raw)
        self.auth_widget.load_settings(self._settings)
        self.filter_widget.load_settings(self._settings)
        self.output_widget.load_settings(self._settings)

    def closeEvent(self, event: QCloseEvent) -> None:
        self.auth_widget.stop_running_threads()
        self.user_search_widget.stop_running_threads()
        if self._export_thread is not None and self._export_thread.isRunning():
            if not self._confirm_close_during_export():
                event.ignore()
                return
            if self._cancel_event is not None:
                self._cancel_event.set()
            self._export_thread.quit()
            if not self._export_thread.wait(2000):
                logger.warning(
                    "Export thread did not stop within timeout: %r",
                    self._export_thread,
                )
        self._settings.setValue("geometry", self.saveGeometry())
        self._settings.setValue("lang", self._lang)
        self.auth_widget.save_settings(self._settings)
        self.filter_widget.save_settings(self._settings)
        self.output_widget.save_settings(self._settings)
        super().closeEvent(event)

    # ------------------------------------------------------------------
    # Export lifecycle
    # ------------------------------------------------------------------

    def _on_export_clicked(self) -> None:
        self.status_widget.stop_progress_display()  # reset any previous run
        config = self._build_config()
        cancel_event = threading.Event()
        self._cancel_event = cancel_event
        worker = ExportWorker(config, self._svc.run_export, cancel_event)
        thread = QThread()
        worker.moveToThread(thread)
        worker.progress_updated.connect(self.status_widget.on_progress_updated)
        worker.log_message.connect(self.status_widget.append_log_line)
        worker.finished.connect(self._on_export_finished)
        worker.failed.connect(self._on_export_failed)
        worker.cancelled.connect(self._on_export_cancelled)
        worker.finished.connect(self._on_export_worker_done)
        worker.failed.connect(self._on_export_worker_done)
        worker.cancelled.connect(self._on_export_worker_done)
        thread.finished.connect(self._clear_export_refs)
        thread.started.connect(worker.run)
        self._export_thread = thread
        self._export_worker = worker
        self.status_widget.export_btn.setEnabled(False)
        self.status_widget.start_progress_display()
        thread.start()

    def _build_config(self) -> ExportConfig:
        config = self.auth_widget.get_export_config_partial()
        config.user_account_ids = self.user_search_widget.get_selected_account_ids()
        from_qdate = self.filter_widget.from_date.date()
        to_qdate = self.filter_widget.to_date.date()
        config.from_date = date(from_qdate.year(), from_qdate.month(), from_qdate.day())
        config.to_date = date(to_qdate.year(), to_qdate.month(), to_qdate.day())
        config.project_keys = self.filter_widget.get_project_keys()
        config.output_dir = Path(self.output_widget.output_dir_field.text().strip())
        config.delimiter = self.output_widget.delimiter_combo.currentData()
        config.column_profile = ColumnProfile(self.output_widget.column_profile_combo.currentData())
        config.api_version = int(self.output_widget.api_version_combo.currentData())
        return config

    def _on_export_finished(self, output_path: str) -> None:
        self._last_output_path = output_path if output_path else None
        self.status_widget.on_progress_done()
        self.status_widget.hide_cancel_btn()
        msg = (
            f"Export complete. Output: {output_path}"  # i18n: status.log.export_complete
            if output_path
            else "Dry run complete."                   # i18n: status.log.dry_run_complete
        )
        self.status_widget.append_log_line(msg)
        if output_path:
            self.status_widget.show_result_buttons(output_path)
        self._update_export_btn()

    def _on_export_failed(self, message: str) -> None:
        self.status_widget.on_progress_done()
        self.status_widget.hide_cancel_btn()
        self.status_widget.append_log_line(f"Error: {message}")  # i18n: status.log.error
        self._update_export_btn()

    def _clear_export_refs(self) -> None:
        # NOTE: wait() reduces but does not eliminate the OS-thread-cleanup race;
        #       Qt docs note that finished() may fire before thread-local destructors
        #       complete. Full elimination requires a different worker-lifecycle
        #       pattern (see commit message for context). Remove this wait() only
        #       after that refactor.
        if self._export_thread is not None and not self._export_thread.wait(2000):
            logger.warning(
                "Export thread did not stop within timeout: %r",
                self._export_thread,
            )
        self._export_thread = None
        self._export_worker = None
        self._cancel_event = None

    def _on_export_worker_done(self) -> None:
        if self._export_thread is not None:
            self._export_thread.quit()

    def _on_cancel_clicked(self) -> None:
        if self._cancel_event is not None:
            self._cancel_event.set()
        self.status_widget.disable_cancel_btn()
        self.status_widget.append_log_line("Abbruch wird durchgefuehrt...")  # i18n: status.log.cancelling

    def _on_export_cancelled(self) -> None:
        self.status_widget.on_progress_done()
        self.status_widget.hide_cancel_btn()
        self.status_widget.append_log_line("Export abgebrochen.")  # i18n: status.log.cancelled
        self._update_export_btn()

    def _confirm_close_during_export(self) -> bool:
        reply = QMessageBox.question(
            self,
            "Export laeuft",  # i18n: dialog.close_during_export.title
            "Export laeuft. Abbrechen und schliessen?",  # i18n: dialog.close_during_export.text
        )
        return reply == QMessageBox.StandardButton.Yes

    def _on_open_csv_clicked(self) -> None:
        if self._last_output_path:
            QDesktopServices.openUrl(QUrl.fromLocalFile(self._last_output_path))

    def _on_open_folder_clicked(self) -> None:
        if self._last_output_path:
            QDesktopServices.openUrl(
                QUrl.fromLocalFile(str(Path(self._last_output_path).parent))
            )

    # ------------------------------------------------------------------
    # Connection-verify handlers
    # ------------------------------------------------------------------

    def _on_connection_verified(self, config: object) -> None:
        # assert is defensive; PySide6 Signal(object) idiom requires runtime type guard
        assert isinstance(config, ExportConfig)
        self.user_search_widget.set_search_fn(
            lambda query: self._svc.search_users(config, query)
        )

    def _on_connection_invalidated(self) -> None:
        self.user_search_widget.set_search_fn(None)

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def _update_export_btn(self) -> None:
        ok = (
            self.auth_widget.is_valid()
            and self.user_search_widget.is_valid()
            and self.filter_widget.is_valid()
            and self.output_widget.is_valid()
        )
        self.status_widget.set_export_enabled(ok)
        if ok:
            self.status_widget.set_status_text("Ready to export")      # i18n: status.label.ready
        else:
            self.status_widget.set_status_text("Fill in required fields")  # i18n: status.label.not_ready

    # ------------------------------------------------------------------
    # Language toggle
    # ------------------------------------------------------------------

    def _target_flag(self) -> str:
        """Return the flag emoji for the language we would switch to."""
        return "🇬🇧" if self._lang == "de" else "🇩🇪"

    def _toggle_language(self) -> None:
        self._lang = "en" if self._lang == "de" else "de"
        self.lang_btn.setText(self._target_flag())
        self.language_changed.emit(self._lang)
        self._retranslate_all(self._lang)

    def _retranslate_all(self, lang: str) -> None:
        self.auth_widget.retranslate_ui(lang)
        self.user_search_widget.retranslate_ui(lang)
        self.filter_widget.retranslate_ui(lang)
        self.output_widget.retranslate_ui(lang)
        self.status_widget.retranslate_ui(lang)
