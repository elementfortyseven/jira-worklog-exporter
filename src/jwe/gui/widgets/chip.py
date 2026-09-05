"""Small pill-shaped status indicator (JWE-37)."""

from __future__ import annotations

from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QWidget

_INDICATOR_SZ = 8


class Chip(QFrame):
    """Pill with an optional leading indicator and a label.

    ``variant`` is a dynamic property (``ok`` | ``error`` | ``testing`` |
    ``neutral``) driving colors via QSS; the leading indicator is a solid
    dot for ``ok`` and a static (non-animated) spinner ring for ``testing``
    — the real animation lands in JWE-40.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("chip")
        self.setProperty("variant", "neutral")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 4, 10, 4)
        layout.setSpacing(6)

        self._dot = QLabel()
        self._dot.setObjectName("chipDot")
        self._dot.setFixedSize(_INDICATOR_SZ, _INDICATOR_SZ)
        self._dot.hide()

        self._spinner = QLabel()
        self._spinner.setObjectName("chipSpinner")
        self._spinner.setFixedSize(12, 12)
        self._spinner.hide()

        self._label = QLabel()
        self._label.setObjectName("chipLabel")

        layout.addWidget(self._dot)
        layout.addWidget(self._spinner)
        layout.addWidget(self._label)

    def set_state(self, variant: str, label: str) -> None:
        """Set the chip's variant (ok|error|testing|neutral) and label text."""
        self.setProperty("variant", variant)
        self._label.setText(label.upper())
        self._dot.setVisible(variant == "ok")
        self._spinner.setVisible(variant == "testing")
        self.style().unpolish(self)
        self.style().polish(self)
