"""Status bar widget anchored at the bottom of MainWindow (Etappe 1 stub)."""

from __future__ import annotations

from PySide6.QtWidgets import QWidget


class StatusWidget(QWidget):
    """Progress bar, issue/worklog counters, and scrollable log panel."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

    def retranslate_ui(self, lang: str) -> None:
        """Update all translatable strings for *lang*."""
