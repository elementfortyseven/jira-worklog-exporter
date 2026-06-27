"""Numbered section card for the v1.2 visual redesign (JWE-35)."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from jwe.gui.theme.tokens import Accent, Space
from jwe.i18n import DEFAULT_LANG, t

_ICON_SZ = 14  # logical px for section icon content area


def _screen_dpr() -> float:
    """Return the primary screen's device-pixel ratio, or 1.0 if unavailable."""
    app = QApplication.instance()
    if not isinstance(app, QApplication):
        return 1.0
    screen = app.primaryScreen()
    return screen.devicePixelRatio() if screen is not None else 1.0


def _section_icon(name: str, color: QColor, dpr: float = 1.0) -> QPixmap:
    """Paint a section glyph onto a QPixmap and return it (DPI-aware)."""
    from PySide6.QtCore import QPointF, QRectF

    phys = max(1, round(_ICON_SZ * dpr))
    pm = QPixmap(phys, phys)
    pm.setDevicePixelRatio(dpr)
    pm.fill(Qt.GlobalColor.transparent)

    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    pen = QPen(color)
    pen.setWidthF(1.3)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)

    if name == "plug":
        # Two prongs
        p.drawLine(QPointF(4.5, 0.5), QPointF(4.5, 4.5))
        p.drawLine(QPointF(9.5, 0.5), QPointF(9.5, 4.5))
        # Body
        p.drawRoundedRect(QRectF(1.5, 4.5, 11.0, 6.0), 2.0, 2.0)
        # Cable
        p.drawLine(QPointF(7.0, 10.5), QPointF(7.0, 13.5))

    elif name == "users":
        # Head
        p.drawEllipse(QRectF(4.0, 0.5, 6.0, 5.5))
        # Shoulders arc (top half of ellipse below the head)
        p.drawArc(QRectF(0.5, 7.5, 13.0, 8.0), 0, 180 * 16)

    elif name == "calendar":
        # Body
        p.drawRoundedRect(QRectF(0.5, 2.5, 13.0, 11.0), 1.0, 1.0)
        # Header divider
        p.drawLine(QPointF(0.5, 6.5), QPointF(13.5, 6.5))
        # Knobs
        p.drawLine(QPointF(3.5, 0.5), QPointF(3.5, 4.5))
        p.drawLine(QPointF(10.5, 0.5), QPointF(10.5, 4.5))

    elif name == "output":
        # Document body
        p.drawRoundedRect(QRectF(0.5, 0.5, 9.0, 12.0), 1.0, 1.0)
        # Text lines
        p.drawLine(QPointF(2.5, 3.5), QPointF(7.5, 3.5))
        p.drawLine(QPointF(2.5, 6.0), QPointF(7.5, 6.0))
        # Export arrow
        p.drawLine(QPointF(10.5, 6.0), QPointF(13.5, 6.0))
        p.drawLine(QPointF(11.5, 4.0), QPointF(13.5, 6.0))
        p.drawLine(QPointF(11.5, 8.0), QPointF(13.5, 6.0))

    p.end()
    return pm


class SectionCard(QFrame):
    """Numbered section card: icon badge, index/title/subtitle, right-slot, content area."""

    def __init__(
        self,
        index: str,
        icon: str,
        title_key: str,
        subtitle_key: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("sectionCard")
        self._title_key = title_key
        self._subtitle_key = subtitle_key
        self._build_ui(index, icon)
        self.retranslate_ui(DEFAULT_LANG)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self, index: str, icon: str) -> None:
        top, right, bottom, left = Space.CARD_PADDING  # (18, 20, 20, 20)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(left, top, right, bottom)
        outer.setSpacing(Space.FIELD_GAP)

        # ---- Header row ----
        head = QWidget()
        head_layout = QHBoxLayout(head)
        head_layout.setContentsMargins(0, 0, 0, 0)
        head_layout.setSpacing(12)

        # Icon badge
        self._icon_label = QLabel()
        self._icon_label.setObjectName("sectionIcon")
        self._icon_label.setFixedSize(30, 30)
        self._icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._icon_label.setPixmap(_section_icon(icon, QColor(Accent.BASE), _screen_dpr()))
        head_layout.addWidget(self._icon_label)

        # Text column: index, title, subtitle
        text_col = QWidget()
        text_col_layout = QVBoxLayout(text_col)
        text_col_layout.setContentsMargins(0, 0, 0, 0)
        text_col_layout.setSpacing(1)

        self._index_label = QLabel(f"[ {index} ]")
        self._index_label.setObjectName("sectionIndex")
        self._title_label = QLabel()
        self._title_label.setObjectName("sectionTitle")
        self._subtitle_label = QLabel()
        self._subtitle_label.setObjectName("sectionSubtitle")

        text_col_layout.addWidget(self._index_label)
        text_col_layout.addWidget(self._title_label)
        text_col_layout.addWidget(self._subtitle_label)
        head_layout.addWidget(text_col)

        head_layout.addStretch()

        # Right-slot: caller places widgets here via set_head_widget()
        self._head_end = QWidget()
        self._head_end.setObjectName("sectionHeadEnd")
        head_end_layout = QHBoxLayout(self._head_end)
        head_end_layout.setContentsMargins(0, 0, 0, 0)
        head_layout.addWidget(self._head_end)

        outer.addWidget(head)

        # ---- Content area ----
        self._content = QWidget()
        self._content_layout = QVBoxLayout(self._content)
        self._content_layout.setContentsMargins(0, 0, 0, 0)
        self._content_layout.setSpacing(0)
        outer.addWidget(self._content)

        # ---- Accent tick: 26x2 bar at (left, 0) above the padding ----
        self._tick = QFrame(self)
        self._tick.setObjectName("sectionTick")
        self._tick.setFixedSize(26, 2)
        self._tick.move(left, 0)
        self._tick.raise_()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def content_layout(self) -> QVBoxLayout:
        """Return the layout of the content area; caller adds section widgets here."""
        return self._content_layout

    def set_head_widget(self, w: QWidget) -> None:
        """Reparent *w* into the right-slot of the header row."""
        layout = self._head_end.layout()
        assert layout is not None
        layout.addWidget(w)

    def title(self) -> str:
        """Return the current title label text (mirrors QGroupBox.title() for test compat)."""
        return self._title_label.text()

    # ------------------------------------------------------------------
    # i18n
    # ------------------------------------------------------------------

    def retranslate_ui(self, lang: str) -> None:
        """Update title and subtitle for *lang*."""
        self._title_label.setText(t(self._title_key, lang))
        self._subtitle_label.setText(t(self._subtitle_key, lang))
