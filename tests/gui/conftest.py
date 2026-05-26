"""Shared fixtures for GUI tests."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from PySide6.QtCore import QSettings

from jwe.gui.main_window import MainWindow


@pytest.fixture
def isolated_settings(tmp_path: Path) -> QSettings:
    """IniFormat QSettings backed by a temp file — one per test, no OS registry writes."""
    return QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)


@pytest.fixture
def main_window(qtbot, isolated_settings: QSettings) -> MainWindow:
    """MainWindow with isolated settings, registered with qtbot for cleanup."""
    w = MainWindow(_settings=isolated_settings)
    qtbot.addWidget(w)
    return w


@pytest.fixture
def make_main_window(qtbot, isolated_settings: QSettings):
    """Factory fixture: call make_main_window(service=...) to get a MainWindow
    registered with qtbot.

    _windows holds a strong reference to every created window so that
    _close_widgets (which runs before fixture teardown) finds a live weakref
    even when the test stores the window only in a local variable."""
    _windows: list[MainWindow] = []

    def factory(service: Any = None) -> MainWindow:
        w = MainWindow(_settings=isolated_settings, service=service)
        qtbot.addWidget(w)
        _windows.append(w)
        return w

    return factory
