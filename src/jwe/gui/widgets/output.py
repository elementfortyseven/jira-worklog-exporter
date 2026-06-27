"""Output configuration widget (Stage 4)."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSettings, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QWidget,
)

from jwe.config import ColumnProfile
from jwe.i18n import DEFAULT_LANG, t

_DEFAULT_OUTPUT_DIR = "./exports"
_S = "output"


class OutputWidget(QWidget):
    """Output directory, delimiter, column profile, and API-version settings."""

    validation_changed = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._lang: str = DEFAULT_LANG
        Path(_DEFAULT_OUTPUT_DIR).mkdir(exist_ok=True)
        self._build_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        layout = QFormLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        dir_row = QWidget()
        dir_layout = QHBoxLayout(dir_row)
        dir_layout.setContentsMargins(0, 0, 0, 0)
        self.output_dir_field = QLineEdit(_DEFAULT_OUTPUT_DIR)
        self.browse_btn = QPushButton()
        self.browse_btn.setFixedWidth(80)
        dir_layout.addWidget(self.output_dir_field, 1)
        dir_layout.addWidget(self.browse_btn)
        self._lbl_output_dir = QLabel()
        layout.addRow(self._lbl_output_dir, dir_row)

        self.delimiter_combo = QComboBox()
        self.delimiter_combo.addItem("", ",")
        self.delimiter_combo.addItem("", ";")
        self._lbl_delimiter = QLabel()
        layout.addRow(self._lbl_delimiter, self.delimiter_combo)

        self.column_profile_combo = QComboBox()
        for profile in ColumnProfile:
            self.column_profile_combo.addItem(profile.value, profile.value)
        self.column_profile_combo.setCurrentIndex(
            self.column_profile_combo.findData(ColumnProfile.STANDARD.value)
        )
        self._lbl_profile = QLabel()
        layout.addRow(self._lbl_profile, self.column_profile_combo)

        self.api_version_combo = QComboBox()
        self.api_version_combo.addItem("3", 3)
        self.api_version_combo.addItem("2", 2)
        self._lbl_api_version = QLabel()
        layout.addRow(self._lbl_api_version, self.api_version_combo)

        self.output_dir_field.textChanged.connect(lambda _: self.validation_changed.emit())
        self.browse_btn.clicked.connect(self._on_browse)

        self.retranslate_ui(DEFAULT_LANG)

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_browse(self) -> None:
        chosen = QFileDialog.getExistingDirectory(
            self, t("output.browse_dialog.title", self._lang)
        )
        if chosen:
            self.output_dir_field.setText(chosen)

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def is_valid(self) -> bool:
        """Return True when output_dir is non-empty and the path exists on disk."""
        text = self.output_dir_field.text().strip()
        if not text:
            return False
        return Path(text).exists()

    # ------------------------------------------------------------------
    # Settings
    # ------------------------------------------------------------------

    def save_settings(self, settings: QSettings) -> None:
        settings.setValue(f"{_S}/output_dir", self.output_dir_field.text())
        settings.setValue(f"{_S}/delimiter", self.delimiter_combo.currentData())
        settings.setValue(f"{_S}/column_profile", self.column_profile_combo.currentData())
        settings.setValue(f"{_S}/api_version", self.api_version_combo.currentData())

    def load_settings(self, settings: QSettings) -> None:
        output_dir = str(settings.value(f"{_S}/output_dir", _DEFAULT_OUTPUT_DIR))
        self.output_dir_field.setText(output_dir)

        delimiter = str(settings.value(f"{_S}/delimiter", ","))
        idx = self.delimiter_combo.findData(delimiter)
        if idx >= 0:
            self.delimiter_combo.setCurrentIndex(idx)

        profile = str(settings.value(f"{_S}/column_profile", ColumnProfile.STANDARD.value))
        idx = self.column_profile_combo.findData(profile)
        if idx >= 0:
            self.column_profile_combo.setCurrentIndex(idx)

        # QSettings.value() returns object (str or int depending on backend); int(str(...)) handles both.
        api_ver = int(str(settings.value(f"{_S}/api_version", 3)))
        idx = self.api_version_combo.findData(api_ver)
        if idx >= 0:
            self.api_version_combo.setCurrentIndex(idx)

    # ------------------------------------------------------------------
    # i18n
    # ------------------------------------------------------------------

    def retranslate_ui(self, lang: str) -> None:
        """Update all translatable strings for *lang*."""
        self._lang = lang
        self._lbl_output_dir.setText(t("output.label.output_dir", lang))
        self._lbl_delimiter.setText(t("output.label.delimiter", lang))
        self._lbl_profile.setText(t("output.label.profile", lang))
        self._lbl_api_version.setText(t("output.label.api_version", lang))
        self.browse_btn.setText(t("output.btn.browse", lang))
        self.delimiter_combo.setItemText(0, t("output.delimiter.comma", lang))
        self.delimiter_combo.setItemText(1, t("output.delimiter.semicolon", lang))
