"""Output configuration widget (Etappe 1 stub)."""

from __future__ import annotations

from PySide6.QtWidgets import QGroupBox, QWidget


class OutputWidget(QGroupBox):
    """Output directory, delimiter, column profile, and API-version settings."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("Output", parent)  # i18n: section.output.title

    def retranslate_ui(self, lang: str) -> None:
        """Update all translatable strings for *lang*."""
