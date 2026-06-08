"""Date-range and project filter widget (Stage 4)."""

from __future__ import annotations

import re

from PySide6.QtCore import QDate, QSettings, Signal
from PySide6.QtWidgets import (
    QDateEdit,
    QFormLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QWidget,
)

from jwe.i18n import DEFAULT_LANG, t

# Same pattern as config.py and search.py -- do not diverge.
_PROJECT_KEY_RE = re.compile(r"^[A-Z][A-Z0-9_]+$")

_S = "filter"


class FilterWidget(QGroupBox):
    """Date range, project key filter, and export scope configuration."""

    validation_changed = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(t("section.filter.title", DEFAULT_LANG), parent)
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
        self._lbl_from = QLabel()
        layout.addRow(self._lbl_from, self.from_date)

        self.to_date = QDateEdit(last_of_month)
        self.to_date.setCalendarPopup(True)
        self.to_date.setDisplayFormat("yyyy-MM-dd")
        self._lbl_to = QLabel()
        layout.addRow(self._lbl_to, self.to_date)

        self.project_keys_field = QLineEdit()
        self._lbl_projects = QLabel()
        layout.addRow(self._lbl_projects, self.project_keys_field)

        self.from_date.dateChanged.connect(lambda _: self.validation_changed.emit())
        self.to_date.dateChanged.connect(lambda _: self.validation_changed.emit())
        self.project_keys_field.textChanged.connect(lambda _: self.validation_changed.emit())

        self.retranslate_ui(DEFAULT_LANG)

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
        return [tok.strip() for tok in raw.split(",") if tok.strip()]

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
        self.setTitle(t("section.filter.title", lang))
        self._lbl_from.setText(t("filter.label.from", lang))
        self._lbl_to.setText(t("filter.label.to", lang))
        self._lbl_projects.setText(t("filter.label.projects", lang))
        self.project_keys_field.setPlaceholderText(t("filter.project_keys.placeholder", lang))
