"""Custom title bar widget for the frameless main window shell."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QWidget

from jwe.gui.theme import tokens
from jwe.i18n import t


class TitleBar(QFrame):
    """Frameless-window title bar: brand, DE/EN language toggle, window controls."""

    language_selected = Signal(str)
    minimize_requested = Signal()
    maximize_requested = Signal()
    close_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("titleBar")
        self.setFixedHeight(44)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 8, 0)
        layout.setSpacing(6)

        self.brand_label = QLabel()
        self.brand_label.setObjectName("titleBarBrand")
        layout.addWidget(self.brand_label)

        layout.addStretch()

        self.de_btn = QPushButton("DE")
        self.de_btn.setObjectName("titleLangBtn")
        self.de_btn.setProperty("active", False)
        self.de_btn.setFlat(True)

        self.en_btn = QPushButton("EN")
        self.en_btn.setObjectName("titleLangBtn")
        self.en_btn.setProperty("active", False)
        self.en_btn.setFlat(True)

        layout.addWidget(self.de_btn)
        layout.addWidget(self.en_btn)
        layout.addSpacing(8)

        self.win_min_btn = QPushButton("-")
        self.win_min_btn.setObjectName("winMin")
        self.win_min_btn.setFlat(True)

        self.win_max_btn = QPushButton("□")
        self.win_max_btn.setObjectName("winMax")
        self.win_max_btn.setFlat(True)

        self.win_close_btn = QPushButton("X")
        self.win_close_btn.setObjectName("winClose")
        self.win_close_btn.setFlat(True)

        layout.addWidget(self.win_min_btn)
        layout.addWidget(self.win_max_btn)
        layout.addWidget(self.win_close_btn)

        self.de_btn.clicked.connect(lambda: self._on_lang_clicked("de"))
        self.en_btn.clicked.connect(lambda: self._on_lang_clicked("en"))
        self.win_min_btn.clicked.connect(self.minimize_requested)
        self.win_max_btn.clicked.connect(self.maximize_requested)
        self.win_close_btn.clicked.connect(self.close_requested)

    # ------------------------------------------------------------------
    # Language toggle
    # ------------------------------------------------------------------

    def _on_lang_clicked(self, lang: str) -> None:
        self.set_active_lang(lang)
        self.language_selected.emit(lang)

    def set_active_lang(self, lang: str) -> None:
        """Update the active button highlight for the given language code."""
        for btn, btn_lang in ((self.de_btn, "de"), (self.en_btn, "en")):
            btn.setProperty("active", lang == btn_lang)
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def retranslate_ui(self, lang: str) -> None:
        title = t("app.title", lang)
        emphasized = title.replace(
            "Worklog",
            f"<b style='color:{tokens.Accent.BASE}'>Worklog</b>",
        )
        self.brand_label.setText(emphasized)

    # ------------------------------------------------------------------
    # Mouse events: window drag + double-click maximize
    # ------------------------------------------------------------------

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if (
            event.button() == Qt.MouseButton.LeftButton
            and self.childAt(event.position().toPoint()) is None
        ):
            win = self.window()
            handle = win.windowHandle() if win is not None else None
            if handle is not None:
                handle.startSystemMove()
                return
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.maximize_requested.emit()
        super().mouseDoubleClickEvent(event)
