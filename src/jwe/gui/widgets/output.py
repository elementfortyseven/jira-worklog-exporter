"""Output configuration widget (Etappe 4)."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSettings, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QWidget,
)

from jwe.config import ColumnProfile

_DEFAULT_OUTPUT_DIR = "./exports"
_S = "output"


class OutputWidget(QGroupBox):
    """Output directory, delimiter, column profile, and API-version settings."""

    validation_changed = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("Output", parent)  # i18n: section.output.title
        Path(_DEFAULT_OUTPUT_DIR).mkdir(exist_ok=True)
        self._build_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        layout = QFormLayout(self)
        layout.setContentsMargins(8, 16, 8, 8)

        dir_row = QWidget()
        dir_layout = QHBoxLayout(dir_row)
        dir_layout.setContentsMargins(0, 0, 0, 0)
        self.output_dir_field = QLineEdit(_DEFAULT_OUTPUT_DIR)
        self.browse_btn = QPushButton("Browse...")  # i18n: output.btn.browse
        self.browse_btn.setFixedWidth(80)
        dir_layout.addWidget(self.output_dir_field, 1)
        dir_layout.addWidget(self.browse_btn)
        layout.addRow("Output Dir", dir_row)  # i18n: output.label.output_dir

        self.delimiter_combo = QComboBox()
        self.delimiter_combo.addItem(", (Comma)", ",")     # i18n: output.delimiter.comma
        self.delimiter_combo.addItem("; (Semicolon)", ";")  # i18n: output.delimiter.semicolon
        layout.addRow("Delimiter", self.delimiter_combo)   # i18n: output.label.delimiter

        self.column_profile_combo = QComboBox()
        for profile in ColumnProfile:
            self.column_profile_combo.addItem(profile.value, profile.value)
        self.column_profile_combo.setCurrentIndex(
            self.column_profile_combo.findData(ColumnProfile.STANDARD.value)
        )
        layout.addRow("Profile", self.column_profile_combo)  # i18n: output.label.profile

        self.api_version_combo = QComboBox()
        self.api_version_combo.addItem("3", 3)
        self.api_version_combo.addItem("2", 2)
        layout.addRow("API Version", self.api_version_combo)  # i18n: output.label.api_version

        self.output_dir_field.textChanged.connect(lambda _: self.validation_changed.emit())
        self.browse_btn.clicked.connect(self._on_browse)

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_browse(self) -> None:
        chosen = QFileDialog.getExistingDirectory(
            self, "Select output directory"  # i18n: output.browse_dialog.title
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
