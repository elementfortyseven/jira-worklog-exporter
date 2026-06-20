"""Design tokens — Technical/Mono direction. Single source of truth.

No Qt import. Mirrors docs/design/tokens.json exactly. All consumer code
(loader, widgets, effects) reads values from here rather than from the JSON.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Color tokens
# ---------------------------------------------------------------------------


class Bg:
    """Background surfaces."""

    CANVAS: str = "#060B13"
    WINDOW: str = "#05090F"
    CARD: str = "#0A1019"
    CARD2: str = "#0B121C"
    INPUT: str = "#060C14"
    INPUT_FOCUS: str = "#0C1826"


class Line:
    """Border / divider colors."""

    HAIRLINE: str = "rgba(120,160,200,0.16)"
    SOFT: str = "rgba(120,160,200,0.08)"
    STRONG: str = "rgba(126,166,206,0.22)"


class Text:
    """Foreground text colors."""

    PRIMARY: str = "#E9EFF7"
    SECONDARY: str = "#93A4BA"
    TERTIARY: str = "#5B6D82"


class Accent:
    """Neon-cyan accent palette."""

    BASE: str = "#22D3EE"
    BRIGHT: str = "#4EE6F7"
    DEEP: str = "#0E7C91"
    INK: str = "#03171C"


class Status:
    """Semantic status colors."""

    OK: str = "#34D399"
    WARN: str = "#FBBF24"
    ERR: str = "#FB7185"


# ---------------------------------------------------------------------------
# Radius tokens (px, int)
# ---------------------------------------------------------------------------


class Radius:
    """Border-radius values for the Mono variant (smaller, sharper)."""

    CONTROL: int = 4
    CARD: int = 6
    WINDOW: int = 10


# ---------------------------------------------------------------------------
# Spacing tokens (px, int)
# ---------------------------------------------------------------------------


class Space:
    """Layout spacing values.

    CARD_PADDING is the 4-tuple (top, right, bottom, left) expanded from the
    CSS shorthand "18px 20px 20px" (top=18, right=left=20, bottom=20).
    """

    WINDOW_PADDING: int = 22
    SECTION_GAP: int = 16
    FIELD_GAP: int = 14
    LABEL_GAP: int = 6
    CARD_PADDING: tuple[int, int, int, int] = (18, 20, 20, 20)
    CARD_PADDING_CSS: str = "18px 20px 20px"


# ---------------------------------------------------------------------------
# Font stacks
# ---------------------------------------------------------------------------


class Font:
    """Font-family stacks for QSS font-family properties."""

    SANS: str = '"Segoe UI", "Helvetica Neue", Helvetica, Arial, system-ui, sans-serif'
    MONO: str = '"JetBrains Mono", ui-monospace, "SF Mono", "Cascadia Code", Menlo, monospace'


# ---------------------------------------------------------------------------
# Type-scale roles
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TypeRole:
    """Typography specification for a single UI role.

    Fields mirror the tokens.json "type" entries. Qt-specific rendering
    (QFont.setLetterSpacing, uppercase in code) is the consumer's concern.
    """

    family: str
    size: float
    weight: int
    transform: str = field(default="")
    letter_spacing: str = field(default="")
    line_height: float = field(default=0.0)
    numeric: str = field(default="")


TYPE: dict[str, TypeRole] = {
    "body": TypeRole(family="mono", size=12, weight=400),
    "sectionTitle": TypeRole(family="sans", size=15, weight=600),
    "sectionSub": TypeRole(family="sans", size=11.5, weight=400),
    "label": TypeRole(
        family="mono",
        size=11,
        weight=600,
        transform="uppercase",
        letter_spacing="0.08em",
    ),
    "value": TypeRole(family="mono", size=12, weight=400),
    "log": TypeRole(family="mono", size=11.5, weight=400, line_height=1.7),
    "counter": TypeRole(family="mono", size=19, weight=600, numeric="tabular-nums"),
    "counterLabel": TypeRole(
        family="sans",
        size=10,
        weight=600,
        transform="uppercase",
        letter_spacing="0.08em",
    ),
    "titlebar": TypeRole(family="mono", size=12.5, weight=500),
    "chip": TypeRole(
        family="mono",
        size=10.5,
        weight=500,
        transform="uppercase",
        letter_spacing="0.07em",
    ),
}

# ---------------------------------------------------------------------------
# Effect data (plain values, no Qt import)
# ---------------------------------------------------------------------------

FOCUS_BORDER_QSS: str = f"border: 1px solid {Accent.BASE}"

# QGraphicsDropShadowEffect parameters; keys: blur_radius, color_rgba (r,g,b,a), x_offset, y_offset
WINDOW_SHADOW: dict[str, int | tuple[int, int, int, int]] = {
    "blur_radius": 60,
    "color_rgba": (0, 0, 0, 200),
    "x_offset": 0,
    "y_offset": 20,
}

NEON_GLOW: dict[str, int | tuple[int, int, int, int]] = {
    "blur_radius": 22,
    "color_rgba": (34, 211, 238, 140),
    "x_offset": 0,
    "y_offset": 0,
}

# ---------------------------------------------------------------------------
# QSS placeholder map
# ---------------------------------------------------------------------------


def qss_vars() -> dict[str, str]:
    """Return the flat %(key)s -> value mapping consumed by app.qss.

    Every %(key)s placeholder used in app.qss must appear here.
    """
    return {
        # Backgrounds
        "bg.canvas": Bg.CANVAS,
        "bg.window": Bg.WINDOW,
        "bg.card": Bg.CARD,
        "bg.card2": Bg.CARD2,
        "bg.input": Bg.INPUT,
        "bg.inputFocus": Bg.INPUT_FOCUS,
        # Lines
        "line.hairline": Line.HAIRLINE,
        "line.soft": Line.SOFT,
        "line.strong": Line.STRONG,
        # Text
        "text.primary": Text.PRIMARY,
        "text.secondary": Text.SECONDARY,
        "text.tertiary": Text.TERTIARY,
        # Accent
        "accent.base": Accent.BASE,
        "accent.bright": Accent.BRIGHT,
        "accent.deep": Accent.DEEP,
        "accent.ink": Accent.INK,
        # Status
        "status.ok": Status.OK,
        "status.warn": Status.WARN,
        "status.err": Status.ERR,
        # Radius (with px suffix for direct QSS use)
        "radius.control": f"{Radius.CONTROL}px",
        "radius.card": f"{Radius.CARD}px",
        "radius.window": f"{Radius.WINDOW}px",
        # Fonts
        "font.sans": Font.SANS,
        "font.mono": Font.MONO,
    }
