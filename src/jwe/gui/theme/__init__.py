"""Theme package — apply_theme() is the public entry point.

Loads JetBrains Mono fonts and renders the QSS template from token values.
Works in both source-tree and PyInstaller-frozen environments.

Qt imports are deferred to function bodies so that importing jwe.gui.theme.tokens
does not load PySide6 at module level (required by the Qt-free import guard).
"""

from __future__ import annotations

import importlib.resources
import logging
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from jwe.gui.theme.tokens import qss_vars

if TYPE_CHECKING:
    from PySide6.QtWidgets import QApplication

__all__ = ["apply_theme"]

logger = logging.getLogger(__name__)

_FONT_FILES: tuple[str, ...] = (
    "JetBrainsMono-Regular.ttf",
    "JetBrainsMono-Medium.ttf",
    "JetBrainsMono-SemiBold.ttf",
)


def _meipass() -> str | None:
    """Return PyInstaller's _MEIPASS directory, or None when running from source."""
    val: str | None = getattr(sys, "_MEIPASS", None)
    return val


def _read_qss() -> str:
    root = _meipass()
    if root:
        return (Path(root) / "jwe" / "gui" / "theme" / "app.qss").read_text(encoding="utf-8")
    return (
        importlib.resources.files("jwe.gui.theme").joinpath("app.qss").read_text(encoding="utf-8")
    )


def _add_font(filename: str) -> None:
    from PySide6.QtGui import QFontDatabase

    root = _meipass()
    if root:
        path = str(Path(root) / "jwe" / "gui" / "theme" / "fonts" / filename)
    else:
        ref = importlib.resources.files("jwe.gui.theme").joinpath("fonts").joinpath(filename)
        with importlib.resources.as_file(ref) as p:
            path = str(p)
    fid = QFontDatabase.addApplicationFont(path)
    if fid == -1:
        logger.warning("Could not load font: %s", filename)


def apply_theme(app: QApplication) -> None:
    """Register bundled fonts and apply the token-driven QSS stylesheet to *app*.

    Call immediately after QApplication.setStyle("Fusion") in gui_main.py.
    Fusion stays as the base style; the stylesheet overrides its colors and radii.
    """
    for fname in _FONT_FILES:
        _add_font(fname)
    template = _read_qss()
    stylesheet = template % qss_vars()
    app.setStyleSheet(stylesheet)
