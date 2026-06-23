"""Custom title bar widget for the frameless main window shell."""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QIcon, QMouseEvent, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QApplication, QFrame, QHBoxLayout, QLabel, QPushButton, QWidget

from jwe.gui.theme import tokens
from jwe.i18n import t

_ICON_SZ = 10  # logical pixels for each window-control icon content area


def _ctrl_icon(shape: str, color: QColor, dpr: float = 1.0) -> QIcon:
    """Paint a window-control glyph onto a QPixmap and return it as a QIcon.

    Half-pixel offsets keep 1px strokes on exact pixel boundaries.
    """
    phys = max(1, round(_ICON_SZ * dpr))
    pm = QPixmap(phys, phys)
    pm.setDevicePixelRatio(dpr)
    pm.fill(Qt.GlobalColor.transparent)

    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, False)
    pen = QPen(color)
    pen.setWidthF(1.0)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)

    if shape == "minimize":
        # Single horizontal bar at vertical centre
        p.drawLine(QPointF(1.5, 4.5), QPointF(8.5, 4.5))

    elif shape == "maximize":
        # Square outline
        p.drawRect(QRectF(1.5, 1.5, 7.0, 7.0))

    elif shape == "restore":
        # Two overlapping offset squares: back (upper-right), front (lower-left)
        p.drawRect(QRectF(3.5, 1.5, 5.0, 5.0))
        p.drawRect(QRectF(1.5, 3.5, 5.0, 5.0))

    elif shape == "close":
        # Diagonal X with slight anti-aliasing for smooth diagonals
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        pen.setWidthF(1.3)
        p.setPen(pen)
        p.drawLine(QPointF(1.5, 1.5), QPointF(8.5, 8.5))
        p.drawLine(QPointF(8.5, 1.5), QPointF(1.5, 8.5))

    p.end()
    return QIcon(pm)


def _screen_dpr() -> float:
    """Return the primary screen's device-pixel ratio, or 1.0 if unavailable."""
    app = QApplication.instance()
    if not isinstance(app, QApplication):
        return 1.0
    screen = app.primaryScreen()
    return screen.devicePixelRatio() if screen is not None else 1.0


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
        self._is_maximized: bool = False

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

        self.win_min_btn = QPushButton()
        self.win_min_btn.setObjectName("winMin")
        self.win_min_btn.setFlat(True)

        self.win_max_btn = QPushButton()
        self.win_max_btn.setObjectName("winMax")
        self.win_max_btn.setFlat(True)

        self.win_close_btn = QPushButton()
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

        self._apply_ctrl_icons()

    # ------------------------------------------------------------------
    # Icon management
    # ------------------------------------------------------------------

    def _apply_ctrl_icons(self) -> None:
        """Set QPainter-drawn icons on the three window control buttons."""
        dpr = _screen_dpr()
        stroke = QColor(tokens.Text.SECONDARY)
        sz = QSize(_ICON_SZ, _ICON_SZ)
        for btn, shape in (
            (self.win_min_btn, "minimize"),
            (self.win_max_btn, "maximize"),
            (self.win_close_btn, "close"),
        ):
            btn.setIcon(_ctrl_icon(shape, stroke, dpr))
            btn.setIconSize(sz)

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

    def set_maximized(self, is_max: bool) -> None:
        """Swap win_max_btn's icon between maximize and restore."""
        self._is_maximized = is_max
        shape = "restore" if is_max else "maximize"
        self.win_max_btn.setIcon(_ctrl_icon(shape, QColor(tokens.Text.SECONDARY), _screen_dpr()))

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
        if event.button() == Qt.MouseButton.LeftButton:
            child = self.childAt(event.position().toPoint())
            if child is None or not isinstance(child, QPushButton):
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
