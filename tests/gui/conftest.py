"""Shared fixtures for GUI tests."""

from __future__ import annotations

from pathlib import Path

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
