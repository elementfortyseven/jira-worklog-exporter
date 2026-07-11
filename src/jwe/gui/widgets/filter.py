"""Date-range and project filter widget (Stage 4)."""

from __future__ import annotations

import re

from PySide6.QtCore import QDate, QSettings, Signal
from PySide6.QtWidgets import (
    QDateEdit,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QWidget,
)

from jwe.gui.theme.tokens import Space
from jwe.i18n import DEFAULT_LANG, t

# Same pattern as config.py and search.py -- do not diverge.
_PROJECT_KEY_RE = re.compile(r"^[A-Z][A-Z0-9_]+$")

_S = "filter"


class FilterWidget(QWidget):
    """Date range, project key filter, and export scope configuration."""

    validation_changed = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._build_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(Space.SECTION_GAP)

        today = QDate.currentDate()
        first_of_month = QDate(today.year(), today.month(), 1)
        last_of_month = first_of_month.addMonths(1).addDays(-1)

        # Left column: From / To. FieldsStayAtSizeHint keeps the date edits at
        # their natural width so the calendar dropdown stays next to the field
        # instead of stretching to the window edge.
        date_form = QFormLayout()
        date_form.setContentsMargins(0, 0, 0, 0)
        date_form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.FieldsStayAtSizeHint)

        self.from_date = QDateEdit(first_of_month)
        self.from_date.setCalendarPopup(True)
        self.from_date.setDisplayFormat("yyyy-MM-dd")
        self._lbl_from = QLabel()
        date_form.addRow(self._lbl_from, self.from_date)

        self.to_date = QDateEdit(last_of_month)
        self.to_date.setCalendarPopup(True)
        self.to_date.setDisplayFormat("yyyy-MM-dd")
        self._lbl_to = QLabel()
        date_form.addRow(self._lbl_to, self.to_date)

        # Right column: Projects -- the line edit fills the remaining width.
        project_form = QFormLayout()
        project_form.setContentsMargins(0, 0, 0, 0)

        self.project_keys_field = QLineEdit()
        self._lbl_projects = QLabel()
        project_form.addRow(self._lbl_projects, self.project_keys_field)

        layout.addLayout(date_form)
        layout.addLayout(project_form, 1)

        self.from_date.dateChanged.connect(lambda _: self._on_field_changed())
        self.to_date.dateChanged.connect(lambda _: self._on_field_changed())
        self.project_keys_field.textChanged.connect(lambda _: self._on_field_changed())

        self.retranslate_ui(DEFAULT_LANG)

    # ------------------------------------------------------------------
    # Field-change dispatcher
    # ------------------------------------------------------------------

    def _on_field_changed(self) -> None:
        """Update invalid styling first, then notify listeners.

        Keeping _update_invalid_state before validation_changed.emit() means
        external listeners already see the updated [invalid] property.
        setProperty/unpolish/polish do not emit dateChanged or textChanged,
        so there is no signal loop.
        """
        self._update_invalid_state()
        self.validation_changed.emit()

    def _update_invalid_state(self) -> None:
        """Set [invalid] on date and project-key fields; guard avoids spurious re-polish."""
        date_inv = self.from_date.date() > self.to_date.date()
        for widget in (self.from_date, self.to_date):
            if widget.property("invalid") != date_inv:
                widget.setProperty("invalid", date_inv)
                widget.style().unpolish(widget)
                widget.style().polish(widget)

        raw = self.project_keys_field.text().strip()
        proj_inv = bool(raw) and not all(
            _PROJECT_KEY_RE.match(tok.strip()) for tok in raw.split(",")
        )
        field = self.project_keys_field
        if field.property("invalid") != proj_inv:
            field.setProperty("invalid", proj_inv)
            field.style().unpolish(field)
            field.style().polish(field)

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
        self._lbl_from.setText(t("filter.label.from", lang))
        self._lbl_to.setText(t("filter.label.to", lang))
        self._lbl_projects.setText(t("filter.label.projects", lang))
        self.project_keys_field.setPlaceholderText(t("filter.project_keys.placeholder", lang))
