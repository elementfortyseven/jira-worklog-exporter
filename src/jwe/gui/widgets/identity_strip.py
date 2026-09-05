"""Connected-identity strip with click-to-copy account ID (JWE-37)."""

from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication, QHBoxLayout, QLabel, QWidget

from jwe.i18n import DEFAULT_LANG, t

_COPY_CONFIRMATION_MS = 1200


class IdentityStrip(QWidget):
    """Thin bar shown once a connection is verified; hidden otherwise."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("idStrip")
        self._lang: str = DEFAULT_LANG
        self._display_name: str = ""
        self._account_id: str = ""

        layout = QHBoxLayout(self)
        layout.setContentsMargins(22, 9, 22, 9)
        layout.setSpacing(10)

        self._dot = QLabel()
        self._dot.setObjectName("idStripDot")
        self._dot.setFixedSize(8, 8)

        self._label = QLabel()
        self._label.setObjectName("idStripLabel")

        layout.addWidget(self._dot)
        layout.addWidget(self._label, 1)

        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self._revert_timer = QTimer(self)
        self._revert_timer.setSingleShot(True)
        self._revert_timer.timeout.connect(self._revert_label)

        self.hide()

    def set_identity(self, name: str, account_id: str) -> None:
        """Show the strip with *name* and store *account_id* for copy/tooltip."""
        self._display_name = name
        self._account_id = account_id
        self._label.setText(t("idstrip.connected_as", self._lang, name=name))
        self.setToolTip(f"{account_id}\n{t('idstrip.copy_hint', self._lang)}")
        self.show()

    def clear(self) -> None:
        """Hide the strip and forget the stored identity."""
        self._display_name = ""
        self._account_id = ""
        self.hide()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Copy the full account ID to the clipboard and flash a confirmation."""
        if self._account_id:
            clipboard = QApplication.clipboard()
            if clipboard is not None:
                clipboard.setText(self._account_id)
            self._label.setText(t("idstrip.copied", self._lang))
            self._revert_timer.start(_COPY_CONFIRMATION_MS)
        super().mousePressEvent(event)

    def _revert_label(self) -> None:
        if self._display_name:
            self._label.setText(t("idstrip.connected_as", self._lang, name=self._display_name))

    def retranslate_ui(self, lang: str) -> None:
        """Update label/tooltip text for *lang*, if an identity is currently shown."""
        self._lang = lang
        if self._display_name:
            self._label.setText(t("idstrip.connected_as", lang, name=self._display_name))
            self.setToolTip(f"{self._account_id}\n{t('idstrip.copy_hint', lang)}")
