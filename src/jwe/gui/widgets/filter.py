"""Date-range and project filter widget (Etappe 4)."""

from __future__ import annotations

import re

from PySide6.QtCore import QDate, QSettings, Signal
from PySide6.QtWidgets import (
    QDateEdit,
    QFormLayout,
    QGroupBox,
    QLineEdit,
    QWidget,
)

# Same pattern as config.py and search.py -- do not diverge.
_PROJECT_KEY_RE = re.compile(r"^[A-Z][A-Z0-9_]+$")

_S = "filter"


class FilterWidget(QGroupBox):
    """Date range, project key filter, and export scope configuration."""

    validation_changed = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("Date & Project Filter", parent)  # i18n: section.filter.title
        self._build_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        layout = QFormLayout(self)
        layout.setContentsMargins(8, 16, 8, 8)

        today = QDate.currentDate()
        first_of_month = QDate(today.year(), today.month(), 1)
        last_of_month = first_of_month.addMonths(1).addDays(-1)

        self.from_date = QDateEdit(first_of_month)
        self.from_date.setCalendarPopup(True)
        self.from_date.setDisplayFormat("yyyy-MM-dd")
        layout.addRow("From", self.from_date)  # i18n: filter.label.from

        self.to_date = QDateEdit(last_of_month)
        self.to_date.setCalendarPopup(True)
        self.to_date.setDisplayFormat("yyyy-MM-dd")
        layout.addRow("To", self.to_date)  # i18n: filter.label.to

        self.project_keys_field = QLineEdit()
        self.project_keys_field.setPlaceholderText(
            "PROJ, SUPP (optional)"  # i18n: filter.project_keys.placeholder
        )
        layout.addRow("Projects", self.project_keys_field)  # i18n: filter.label.projects

        self.from_date.dateChanged.connect(lambda _: self.validation_changed.emit())
        self.to_date.dateChanged.connect(lambda _: self.validation_changed.emit())
        self.project_keys_field.textChanged.connect(lambda _: self.validation_changed.emit())

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def is_valid(self) -> bool:
        """Return True when date range is non-inverted and every project key is well-formed."""
        if self.from_date.date() > self.to_date.date():
            return False
        raw = self.project_keys_field.text().strip()
        if not raw:
            return True
        return all(_PROJECT_KEY_RE.match(token.strip()) for token in raw.split(","))

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_project_keys(self) -> list[str]:
        """Return the parsed list of project keys; empty list when field is blank."""
        raw = self.project_keys_field.text().strip()
        if not raw:
            return []
        return [t.strip() for t in raw.split(",") if t.strip()]

    # ------------------------------------------------------------------
    # Settings
    # ------------------------------------------------------------------

    def save_settings(self, settings: QSettings) -> None:
        """Persist project_keys only; dates are session-specific and not saved."""
        settings.setValue(f"{_S}/project_keys", self.project_keys_field.text())

    def load_settings(self, settings: QSettings) -> None:
        self.project_keys_field.setText(str(settings.value(f"{_S}/project_keys", "")))

    # ------------------------------------------------------------------
    # i18n
    # ------------------------------------------------------------------

    def retranslate_ui(self, lang: str) -> None:
        """Update all translatable strings for *lang*."""
