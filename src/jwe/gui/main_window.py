"""Main application window."""

from __future__ import annotations

import logging
import threading
from datetime import date
from pathlib import Path
from typing import Any, cast

from PySide6.QtCore import QByteArray, QPoint, QSettings, Qt, QThread, QUrl, Signal
from PySide6.QtGui import (
    QCloseEvent,
    QColor,
    QDesktopServices,
    QMouseEvent,
)
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
    QMainWindow,
    QMessageBox,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

import jwe.service as _default_svc
from jwe.config import ColumnProfile, ExportConfig
from jwe.gui.theme.tokens import WINDOW_SHADOW
from jwe.gui.widgets.auth import AuthWidget
from jwe.gui.widgets.filter import FilterWidget
from jwe.gui.widgets.output import OutputWidget
from jwe.gui.widgets.status import StatusWidget
from jwe.gui.widgets.title_bar import TitleBar
from jwe.gui.widgets.user_search import UserSearchWidget
from jwe.gui.workers.export_worker import ExportWorker
from jwe.i18n import diag, t

logger = logging.getLogger(__name__)

_SETTINGS_ORG = "jira-worklog-exporter"
_SETTINGS_APP = "jwe-gui"
_SHADOW_MARGIN = 10
_RESIZE_MARGIN = 6


class MainWindow(QMainWindow):
    """Top-level application window; orchestrates all section widgets."""

    language_changed = Signal(str)
    _start_export_requested = Signal(object, object)

    def __init__(
        self,
        *,
        initial_lang: str | None = None,
        _settings: QSettings | None = None,
        service: Any = None,
    ) -> None:
        super().__init__()
        self._settings: QSettings = _settings or QSettings(_SETTINGS_ORG, _SETTINGS_APP)
        self._lang: str = "de"
        self._svc: Any = service if service is not None else _default_svc
        self._cancel_event: threading.Event | None = None
        self._export_active: bool = False
        self._last_output_path: str | None = None
        self._maximized: bool = False
        self._pre_max_geometry: QByteArray | None = None
        self._shadow_effect: QGraphicsDropShadowEffect | None = None

        self.auth_widget = AuthWidget(service=self._svc)
        self.user_search_widget = UserSearchWidget()
        self.filter_widget = FilterWidget()
        self.output_widget = OutputWidget()
        self.status_widget = StatusWidget()
        self.title_bar = TitleBar()

        self._export_worker = ExportWorker(self._svc.run_export)
        self._export_thread = QThread()
        self._export_worker.moveToThread(self._export_thread)
        self._start_export_requested.connect(self._export_worker.start_export)
        self._export_worker.progress_updated.connect(self.status_widget.on_progress_updated)
        self._export_worker.log_message.connect(self.status_widget.append_log_line)
        self._export_worker.finished.connect(self._on_export_finished)
        self._export_worker.failed.connect(self._on_export_failed)
        self._export_worker.cancelled.connect(self._on_export_cancelled)

        self._build_ui()
        self._restore_settings(initial_lang)
        self._update_export_btn()
        self._retranslate_all(self._lang)
        self.status_widget.export_btn.clicked.connect(self._on_export_clicked)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        self.setWindowTitle(t("app.title", self._lang))
        self.setMinimumSize(800, 600)
        self.resize(960, 720)

        # Frameless + transparent so the drop shadow renders into the margin.
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        central = QWidget()
        self.setCentralWidget(central)
        central.setMouseTracking(True)
        self.setMouseTracking(True)

        outer_layout = QVBoxLayout(central)
        outer_layout.setContentsMargins(
            _SHADOW_MARGIN, _SHADOW_MARGIN, _SHADOW_MARGIN, _SHADOW_MARGIN
        )
        outer_layout.setSpacing(0)

        # Visible window frame — background, border, border-radius.
        self._window_frame = QFrame()
        self._window_frame.setObjectName("windowFrame")
        self._window_frame.setProperty("maximized", False)
        outer_layout.addWidget(self._window_frame)

        # Drop shadow on the frame.
        shadow = QGraphicsDropShadowEffect(self._window_frame)
        color_rgba = cast(tuple[int, int, int, int], WINDOW_SHADOW["color_rgba"])
        shadow.setColor(QColor(*color_rgba))
        shadow.setBlurRadius(cast(int, WINDOW_SHADOW["blur_radius"]))
        shadow.setXOffset(cast(int, WINDOW_SHADOW["x_offset"]))
        shadow.setYOffset(cast(int, WINDOW_SHADOW["y_offset"]))
        self._window_frame.setGraphicsEffect(shadow)
        self._shadow_effect = shadow

        frame_layout = QVBoxLayout(self._window_frame)
        frame_layout.setContentsMargins(0, 0, 0, 0)
        frame_layout.setSpacing(0)

        frame_layout.addWidget(self.title_bar)

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
        frame_layout.addWidget(scroll, 1)
        frame_layout.addWidget(self.status_widget)

        # Title bar signals.
        self.title_bar.language_selected.connect(self._on_language_selected)
        self.title_bar.minimize_requested.connect(self.showMinimized)
        self.title_bar.maximize_requested.connect(self._toggle_max_restore)
        self.title_bar.close_requested.connect(self.close)

        # Validation wiring.
        self.auth_widget.validation_changed.connect(self._update_export_btn)
        self.user_search_widget.selection_changed.connect(self._update_export_btn)
        self.filter_widget.validation_changed.connect(self._update_export_btn)
        self.output_widget.validation_changed.connect(self._update_export_btn)

        self.auth_widget.connection_verified.connect(self._on_connection_verified)
        self.auth_widget.connection_invalidated.connect(self._on_connection_invalidated)

        self.status_widget.open_csv_btn.clicked.connect(self._on_open_csv_clicked)
        self.status_widget.open_folder_btn.clicked.connect(self._on_open_folder_clicked)
        self.status_widget.cancel_requested.connect(self._on_cancel_clicked)

    # ------------------------------------------------------------------
    # Settings persistence
    # ------------------------------------------------------------------

    def _restore_settings(self, initial_lang: str | None) -> None:
        saved_lang = cast(str, self._settings.value("lang", "de"))
        self._lang = initial_lang if initial_lang is not None else saved_lang
        self.title_bar.set_active_lang(self._lang)
        geo_raw = self._settings.value("geometry", QByteArray())
        if isinstance(geo_raw, QByteArray) and not geo_raw.isEmpty():
            self.restoreGeometry(geo_raw)
        self.auth_widget.load_settings(self._settings)
        self.filter_widget.load_settings(self._settings)
        self.output_widget.load_settings(self._settings)

    def closeEvent(self, event: QCloseEvent) -> None:
        self.auth_widget.stop_running_threads()
        self.user_search_widget.stop_running_threads()
        if self._export_active:
            if not self._confirm_close_during_export():
                event.ignore()
                return
            if self._cancel_event is not None:
                self._cancel_event.set()
        if self._export_thread.isRunning():
            self._export_thread.quit()
            if not self._export_thread.wait(2000):
                logger.warning(
                    "Export thread did not stop within timeout: %r",
                    self._export_thread,
                )
        # Save the non-maximized geometry so a restore doesn't start maximized.
        if self._maximized and self._pre_max_geometry is not None:
            self._settings.setValue("geometry", self._pre_max_geometry)
        else:
            self._settings.setValue("geometry", self.saveGeometry())
        self._settings.setValue("lang", self._lang)
        self.auth_widget.save_settings(self._settings)
        self.filter_widget.save_settings(self._settings)
        self.output_widget.save_settings(self._settings)
        super().closeEvent(event)

    # ------------------------------------------------------------------
    # Maximize / restore
    # ------------------------------------------------------------------

    def _toggle_max_restore(self) -> None:
        outer_layout = cast(QVBoxLayout, self.centralWidget().layout())
        if self._maximized:
            self._maximized = False
            if self._shadow_effect is not None:
                self._shadow_effect.setEnabled(True)
            self._window_frame.setProperty("maximized", False)
            self._window_frame.style().unpolish(self._window_frame)
            self._window_frame.style().polish(self._window_frame)
            outer_layout.setContentsMargins(
                _SHADOW_MARGIN, _SHADOW_MARGIN, _SHADOW_MARGIN, _SHADOW_MARGIN
            )
            if self._pre_max_geometry is not None:
                self.restoreGeometry(self._pre_max_geometry)
        else:
            self._pre_max_geometry = self.saveGeometry()
            self._maximized = True
            if self._shadow_effect is not None:
                self._shadow_effect.setEnabled(False)
            self._window_frame.setProperty("maximized", True)
            self._window_frame.style().unpolish(self._window_frame)
            self._window_frame.style().polish(self._window_frame)
            outer_layout.setContentsMargins(0, 0, 0, 0)
            screen = self.screen()
            if screen is not None:
                self.setGeometry(screen.availableGeometry())

    # ------------------------------------------------------------------
    # Edge resize via startSystemResize
    # ------------------------------------------------------------------

    def _edge_at_pos(self, pos: QPoint) -> Qt.Edge | None:
        # Detect edges against the window outer rect. The transparent margin
        # (width _SHADOW_MARGIN) has no interactive children, so mouse events
        # reach MainWindow there. _RESIZE_MARGIN < _SHADOW_MARGIN keeps the
        # band entirely outside #windowFrame content.
        r = self.rect()
        m = _RESIZE_MARGIN

        edges: Qt.Edge = Qt.Edge(0)
        if pos.x() <= r.left() + m:
            edges |= Qt.Edge.LeftEdge
        elif pos.x() >= r.right() - m:
            edges |= Qt.Edge.RightEdge
        if pos.y() <= r.top() + m:
            edges |= Qt.Edge.TopEdge
        elif pos.y() >= r.bottom() - m:
            edges |= Qt.Edge.BottomEdge

        return edges if edges else None

    def _set_resize_cursor(self, edges: Qt.Edge) -> None:
        top = bool(edges & Qt.Edge.TopEdge)
        bottom = bool(edges & Qt.Edge.BottomEdge)
        left = bool(edges & Qt.Edge.LeftEdge)
        right = bool(edges & Qt.Edge.RightEdge)

        if (top and left) or (bottom and right):
            self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        elif (top and right) or (bottom and left):
            self.setCursor(Qt.CursorShape.SizeBDiagCursor)
        elif left or right:
            self.setCursor(Qt.CursorShape.SizeHorCursor)
        else:
            self.setCursor(Qt.CursorShape.SizeVerCursor)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if not self._maximized:
            edges = self._edge_at_pos(event.position().toPoint())
            if edges:
                self._set_resize_cursor(edges)
            else:
                self.unsetCursor()
        super().mouseMoveEvent(event)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton and not self._maximized:
            edges = self._edge_at_pos(event.position().toPoint())
            if edges:
                handle = self.windowHandle()
                if handle is not None:
                    handle.startSystemResize(edges)
                    return
        super().mousePressEvent(event)

    # ------------------------------------------------------------------
    # Export lifecycle
    # ------------------------------------------------------------------

    def _on_export_clicked(self) -> None:
        self.status_widget.stop_progress_display()
        config = self._build_config()
        self._cancel_event = threading.Event()
        self._export_active = True
        self.status_widget.export_btn.setEnabled(False)
        self.status_widget.start_progress_display()
        if not self._export_thread.isRunning():
            self._export_thread.start()
        self._start_export_requested.emit(config, self._cancel_event)

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
        self._export_active = False
        self._last_output_path = output_path if output_path else None
        self.status_widget.on_progress_done()
        self.status_widget.hide_cancel_btn()
        msg = (
            diag("status.log.export_complete", path=output_path)
            if output_path
            else diag("status.log.dry_run_complete")
        )
        self.status_widget.append_log_line(msg)
        if output_path:
            self.status_widget.show_result_buttons(output_path)
        self._update_export_btn()

    def _on_export_failed(self, message: str) -> None:
        self._export_active = False
        self.status_widget.on_progress_done()
        self.status_widget.hide_cancel_btn()
        self.status_widget.append_log_line(diag("status.log.error", message=message))
        self._update_export_btn()

    def _on_cancel_clicked(self) -> None:
        if self._cancel_event is not None:
            self._cancel_event.set()
        self.status_widget.disable_cancel_btn()
        self.status_widget.append_log_line(diag("status.log.cancelling"))

    def _on_export_cancelled(self) -> None:
        self._export_active = False
        self.status_widget.on_progress_done()
        self.status_widget.hide_cancel_btn()
        self.status_widget.append_log_line(diag("status.log.cancelled"))
        self._update_export_btn()

    def _confirm_close_during_export(self) -> bool:
        reply = QMessageBox.question(
            self,
            t("dialog.close_during_export.title", self._lang),
            t("dialog.close_during_export.text", self._lang),
        )
        return reply == QMessageBox.StandardButton.Yes

    def _on_open_csv_clicked(self) -> None:
        if self._last_output_path:
            QDesktopServices.openUrl(QUrl.fromLocalFile(self._last_output_path))

    def _on_open_folder_clicked(self) -> None:
        if self._last_output_path:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(Path(self._last_output_path).parent)))

    # ------------------------------------------------------------------
    # Connection-verify handlers
    # ------------------------------------------------------------------

    def _on_connection_verified(self, config: object) -> None:
        assert isinstance(config, ExportConfig)
        self.user_search_widget.set_search_fn(lambda query: self._svc.search_users(config, query))

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
            self.status_widget.set_status_text(t("status.label.ready", self._lang))
        else:
            self.status_widget.set_status_text(t("status.label.not_ready", self._lang))

    # ------------------------------------------------------------------
    # Language selection
    # ------------------------------------------------------------------

    def _on_language_selected(self, lang: str) -> None:
        if lang == self._lang:
            return
        self._lang = lang
        self.language_changed.emit(lang)
        self._retranslate_all(lang)

    def _retranslate_all(self, lang: str) -> None:
        self.setWindowTitle(t("app.title", lang))
        self.title_bar.retranslate_ui(lang)
        self.auth_widget.retranslate_ui(lang)
        self.user_search_widget.retranslate_ui(lang)
        self.filter_widget.retranslate_ui(lang)
        self.output_widget.retranslate_ui(lang)
        self.status_widget.retranslate_ui(lang)
        self._update_export_btn()
