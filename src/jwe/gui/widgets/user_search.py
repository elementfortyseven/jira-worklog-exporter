"""User search and selection shuttle widget (Etappe 1 stub)."""

from __future__ import annotations

from PySide6.QtWidgets import QGroupBox, QWidget


class UserSearchWidget(QGroupBox):
    """Search for Jira users and build the selected-users list."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("Users", parent)  # i18n: section.user_search.title

    def retranslate_ui(self, lang: str) -> None:
        """Update all translatable strings for *lang*."""
