"""Status bar widget anchored at the bottom of MainWindow (Etappe 4 partial fill)."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QWidget,
)


class StatusWidget(QWidget):
    """Export button, status label, and (Etappe 5) progress/log panel."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)

        self.export_btn = QPushButton("Start Export")  # i18n: status.btn.export
        self.export_btn.setEnabled(False)
        layout.addWidget(self.export_btn)

        self.status_label = QLabel("Fill in required fields")  # i18n: status.label.not_ready
        layout.addWidget(self.status_label, 1)

    # ------------------------------------------------------------------
    # Public API (called by MainWindow._update_export_btn)
    # ------------------------------------------------------------------

    def set_export_enabled(self, enabled: bool) -> None:
        self.export_btn.setEnabled(enabled)

    def set_status_text(self, text: str) -> None:
        self.status_label.setText(text)

    # ------------------------------------------------------------------
    # i18n
    # ------------------------------------------------------------------

    def retranslate_ui(self, lang: str) -> None:
        """Update all translatable strings for *lang*."""
