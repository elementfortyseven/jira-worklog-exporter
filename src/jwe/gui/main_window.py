"""Main application window."""

from __future__ import annotations

from typing import Any, cast

from PySide6.QtCore import QByteArray, QSettings, Qt, Signal
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QHBoxLayout,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

import jwe.service as _default_svc
from jwe.gui.widgets.auth import AuthWidget
from jwe.gui.widgets.filter import FilterWidget
from jwe.gui.widgets.output import OutputWidget
from jwe.gui.widgets.status import StatusWidget
from jwe.gui.widgets.user_search import UserSearchWidget

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
        _svc: Any = service if service is not None else _default_svc

        self.auth_widget = AuthWidget(service=_svc)
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
        self._settings.setValue("geometry", self.saveGeometry())
        self._settings.setValue("lang", self._lang)
        self.auth_widget.save_settings(self._settings)
        self.filter_widget.save_settings(self._settings)
        self.output_widget.save_settings(self._settings)
        super().closeEvent(event)

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
