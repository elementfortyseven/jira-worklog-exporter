"""PySide6 GUI package for the Jira Worklog Exporter."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from jwe.gui.main_window import MainWindow

__all__ = ["MainWindow"]


def __getattr__(name: str) -> object:
    """Lazy re-export so that importing jwe.gui submodules does not load Qt."""
    if name == "MainWindow":
        from jwe.gui.main_window import MainWindow

        return MainWindow
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
