"""Date-range and project filter widget (Etappe 1 stub)."""

from __future__ import annotations

from PySide6.QtWidgets import QGroupBox, QWidget


class FilterWidget(QGroupBox):
    """Date range, project key filter, and export scope configuration."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("Filter", parent)  # i18n: section.filter.title

    def retranslate_ui(self, lang: str) -> None:
        """Update all translatable strings for *lang*."""
