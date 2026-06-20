"""Tests for jwe.gui.theme — tokens, QSS template, apply_theme() loader."""

from __future__ import annotations

import importlib.resources
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

import jwe.gui.theme.tokens as tok
from jwe.gui.theme.tokens import TYPE, TypeRole, qss_vars

# ---------------------------------------------------------------------------
# Path to the canonical tokens.json source
# ---------------------------------------------------------------------------

_TOKENS_JSON = Path(__file__).parent.parent.parent / "docs" / "design" / "tokens.json"


@pytest.fixture(scope="module")
def token_data() -> dict[str, Any]:
    return json.loads(_TOKENS_JSON.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Drift guard — parametrized: every color / radius / space / font / type value
# ---------------------------------------------------------------------------

_COLOR_CASES: list[tuple[str, str]] = [
    ("color.bg.canvas", tok.Bg.CANVAS),
    ("color.bg.window", tok.Bg.WINDOW),
    ("color.bg.card", tok.Bg.CARD),
    ("color.bg.card2", tok.Bg.CARD2),
    ("color.bg.input", tok.Bg.INPUT),
    ("color.bg.inputFocus", tok.Bg.INPUT_FOCUS),
    ("color.line.hairline", tok.Line.HAIRLINE),
    ("color.line.soft", tok.Line.SOFT),
    ("color.line.strong", tok.Line.STRONG),
    ("color.text.primary", tok.Text.PRIMARY),
    ("color.text.secondary", tok.Text.SECONDARY),
    ("color.text.tertiary", tok.Text.TERTIARY),
    ("color.accent.base", tok.Accent.BASE),
    ("color.accent.bright", tok.Accent.BRIGHT),
    ("color.accent.deep", tok.Accent.DEEP),
    ("color.accent.ink", tok.Accent.INK),
    ("color.status.ok", tok.Status.OK),
    ("color.status.warn", tok.Status.WARN),
    ("color.status.err", tok.Status.ERR),
]


@pytest.mark.parametrize(
    "json_path,actual",
    _COLOR_CASES,
    ids=[c[0] for c in _COLOR_CASES],
)
def test_color_token_matches_json(token_data: dict[str, Any], json_path: str, actual: str) -> None:
    keys = json_path.split(".")
    expected: Any = token_data
    for k in keys:
        expected = expected[k]
    assert actual == expected, f"{json_path}: {actual!r} != {expected!r}"


_RADIUS_CASES: list[tuple[str, int]] = [
    ("radius.control", tok.Radius.CONTROL),
    ("radius.card", tok.Radius.CARD),
    ("radius.window", tok.Radius.WINDOW),
]


@pytest.mark.parametrize(
    "json_path,actual",
    _RADIUS_CASES,
    ids=[c[0] for c in _RADIUS_CASES],
)
def test_radius_token_matches_json(token_data: dict[str, Any], json_path: str, actual: int) -> None:
    keys = json_path.split(".")
    expected: Any = token_data
    for k in keys:
        expected = expected[k]
    assert actual == int(expected), f"{json_path}: {actual!r} != {expected!r}"


_SPACE_CASES: list[tuple[str, int]] = [
    ("space.windowPadding", tok.Space.WINDOW_PADDING),
    ("space.sectionGap", tok.Space.SECTION_GAP),
    ("space.fieldGap", tok.Space.FIELD_GAP),
    ("space.labelGap", tok.Space.LABEL_GAP),
]


@pytest.mark.parametrize(
    "json_path,actual",
    _SPACE_CASES,
    ids=[c[0] for c in _SPACE_CASES],
)
def test_space_token_matches_json(token_data: dict[str, Any], json_path: str, actual: int) -> None:
    keys = json_path.split(".")
    expected: Any = token_data
    for k in keys:
        expected = expected[k]
    assert actual == int(expected), f"{json_path}: {actual!r} != {expected!r}"


def test_card_padding_css_matches_json(token_data: dict[str, Any]) -> None:
    assert token_data["space"]["cardPadding"] == tok.Space.CARD_PADDING_CSS


def test_card_padding_tuple_expands_correctly() -> None:
    """(18, 20, 20, 20) is the expanded form of the CSS shorthand '18px 20px 20px'."""
    assert tok.Space.CARD_PADDING == (18, 20, 20, 20)


_FONT_CASES: list[tuple[str, str]] = [
    ("font.sans", tok.Font.SANS),
    ("font.mono", tok.Font.MONO),
]


@pytest.mark.parametrize(
    "json_path,actual",
    _FONT_CASES,
    ids=[c[0] for c in _FONT_CASES],
)
def test_font_stack_matches_json(token_data: dict[str, Any], json_path: str, actual: str) -> None:
    keys = json_path.split(".")
    expected: Any = token_data
    for k in keys:
        expected = expected[k]
    # JSON stores escaped quotes; normalise to compare
    expected_norm = expected.replace('\\"', '"')
    assert actual == expected_norm, f"{json_path}: {actual!r} != {expected_norm!r}"


# Type role drift cases: (role_name, json_key, TypeRole_attr)
_TYPE_BASIC_CASES: list[tuple[str, str, str]] = [
    ("body", "family", "mono"),
    ("body", "weight", "400"),
    ("sectionTitle", "family", "sans"),
    ("sectionTitle", "weight", "600"),
    ("sectionSub", "family", "sans"),
    ("sectionSub", "weight", "400"),
    ("label", "family", "mono"),
    ("label", "weight", "600"),
    ("label", "transform", "uppercase"),
    ("label", "letterSpacing", "0.08em"),
    ("value", "family", "mono"),
    ("value", "weight", "400"),
    ("log", "family", "mono"),
    ("log", "weight", "400"),
    ("log", "lineHeight", "1.7"),
    ("counter", "family", "mono"),
    ("counter", "weight", "600"),
    ("counter", "numeric", "tabular-nums"),
    ("counterLabel", "family", "sans"),
    ("counterLabel", "weight", "600"),
    ("counterLabel", "transform", "uppercase"),
    ("counterLabel", "letterSpacing", "0.08em"),
    ("titlebar", "family", "mono"),
    ("titlebar", "weight", "500"),
    ("chip", "family", "mono"),
    ("chip", "weight", "500"),
    ("chip", "transform", "uppercase"),
    ("chip", "letterSpacing", "0.07em"),
]

# size cases (float comparison)
_TYPE_SIZE_CASES: list[tuple[str, float]] = [
    ("body", 12),
    ("sectionTitle", 15),
    ("sectionSub", 11.5),
    ("label", 11),
    ("value", 12),
    ("log", 11.5),
    ("counter", 19),
    ("counterLabel", 10),
    ("titlebar", 12.5),
    ("chip", 10.5),
]

# JSON camelCase -> TypeRole attribute names
_JSON_TO_ATTR: dict[str, str] = {
    "family": "family",
    "weight": "weight",
    "transform": "transform",
    "letterSpacing": "letter_spacing",
    "lineHeight": "line_height",
    "numeric": "numeric",
}


@pytest.mark.parametrize(
    "role,json_key,expected_str",
    _TYPE_BASIC_CASES,
    ids=[f"type.{r}.{k}" for r, k, _ in _TYPE_BASIC_CASES],
)
def test_type_role_field_matches_json(
    token_data: dict[str, Any],
    role: str,
    json_key: str,
    expected_str: str,
) -> None:
    json_val = token_data["type"][role][json_key]
    attr = _JSON_TO_ATTR[json_key]
    py_val = getattr(TYPE[role], attr)
    assert str(py_val) == str(json_val), (
        f"type.{role}.{json_key}: tokens.py={py_val!r}, json={json_val!r}"
    )


@pytest.mark.parametrize(
    "role,expected_size",
    _TYPE_SIZE_CASES,
    ids=[f"type.{r}.size" for r, _ in _TYPE_SIZE_CASES],
)
def test_type_role_size(role: str, expected_size: float) -> None:
    assert TYPE[role].size == expected_size


def test_type_dict_has_all_ten_roles() -> None:
    expected_roles = {
        "body",
        "sectionTitle",
        "sectionSub",
        "label",
        "value",
        "log",
        "counter",
        "counterLabel",
        "titlebar",
        "chip",
    }
    assert set(TYPE.keys()) == expected_roles


def test_type_role_is_frozen() -> None:
    role: TypeRole = TYPE["body"]
    with pytest.raises(AttributeError):
        role.family = "sans"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Qt-free import guard
# ---------------------------------------------------------------------------


def test_tokens_module_is_qt_free() -> None:
    """tokens.py must not import PySide6 or shiboken6."""
    code = (
        "import jwe.gui.theme.tokens, sys; "
        "assert 'PySide6' not in sys.modules and 'shiboken6' not in sys.modules, "
        "'Qt unexpectedly imported by tokens.py'"
    )
    subprocess.run([sys.executable, "-c", code], check=True)


# ---------------------------------------------------------------------------
# QSS template completeness
# ---------------------------------------------------------------------------


def _load_qss_template() -> str:
    return (
        importlib.resources.files("jwe.gui.theme").joinpath("app.qss").read_text(encoding="utf-8")
    )


def test_qss_vars_covers_all_template_placeholders() -> None:
    """Every %(key)s in app.qss must appear in qss_vars()."""
    template = _load_qss_template()
    placeholders = set(re.findall(r"%\(([^)]+)\)s", template))
    missing = placeholders - set(qss_vars().keys())
    assert not missing, f"qss_vars() missing keys: {missing}"


def test_qss_template_renders_without_leftover_placeholders() -> None:
    """After % substitution the rendered string must have no %(... remnants."""
    template = _load_qss_template()
    rendered = template % qss_vars()
    assert "%(" not in rendered


# ---------------------------------------------------------------------------
# apply_theme() — Qt tests (require QApplication via pytest-qt)
# ---------------------------------------------------------------------------


def test_apply_theme_sets_nonempty_stylesheet(qapp: Any) -> None:
    """apply_theme() produces a non-empty stylesheet on the QApplication."""
    from jwe.gui.theme import apply_theme

    apply_theme(qapp)
    sheet = qapp.styleSheet()
    assert sheet, "stylesheet is empty after apply_theme()"


def test_apply_theme_stylesheet_contains_accent_token(qapp: Any) -> None:
    """Rendered stylesheet must contain the accent.base token value."""
    from jwe.gui.theme import apply_theme
    from jwe.gui.theme.tokens import Accent

    apply_theme(qapp)
    assert Accent.BASE in qapp.styleSheet()


def test_apply_theme_no_unresolved_placeholders(qapp: Any) -> None:
    """Rendered stylesheet must not contain any %(... sequences."""
    from jwe.gui.theme import apply_theme

    apply_theme(qapp)
    assert "%(" not in qapp.styleSheet()


# ---------------------------------------------------------------------------
# Font registration
# ---------------------------------------------------------------------------


def test_jetbrains_mono_registered_after_apply_theme(qapp: Any) -> None:
    """JetBrains Mono must be in QFontDatabase after apply_theme()."""
    from PySide6.QtGui import QFontDatabase

    from jwe.gui.theme import apply_theme

    apply_theme(qapp)
    families = QFontDatabase().families()
    assert "JetBrains Mono" in families, (
        f"JetBrains Mono not found in QFontDatabase; available: {families[:10]}"
    )


def test_font_files_exist_as_package_resources() -> None:
    """All 3 TTF files and OFL.txt must be accessible via importlib.resources."""
    fonts = importlib.resources.files("jwe.gui.theme").joinpath("fonts")
    for filename in (
        "JetBrainsMono-Regular.ttf",
        "JetBrainsMono-Medium.ttf",
        "JetBrainsMono-SemiBold.ttf",
        "OFL.txt",
    ):
        resource = fonts.joinpath(filename)
        assert resource.is_file(), f"Missing package resource: fonts/{filename}"
