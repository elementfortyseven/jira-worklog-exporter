"""Authentication section widget (Etappe 1 stub)."""

from __future__ import annotations

from PySide6.QtWidgets import QGroupBox, QWidget


class AuthWidget(QGroupBox):
    """Collects auth-mode, credentials, and triggers connection test."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("Authentication", parent)  # i18n: section.auth.title

    def retranslate_ui(self, lang: str) -> None:
        """Update all translatable strings for *lang*."""
