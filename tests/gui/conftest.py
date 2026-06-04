"""Shared fixtures for GUI tests."""

from __future__ import annotations

from collections.abc import Generator
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest
from PySide6.QtCore import QSettings

from jwe.gui.main_window import MainWindow


@pytest.fixture(autouse=True)
def mock_keyring(monkeypatch: pytest.MonkeyPatch) -> None:
    """Prevent the real Windows keyring backend from firing in every GUI test.

    Patches jwe.service.keyring.get_password to return None so load_token
    finds no stored token without touching the OS credential store.
    raising=False is belt-and-suspenders for the degraded case where the
    optional import fell through and the module alias is None.
    """
    monkeypatch.setattr(
        "jwe.service.keyring.get_password",
        lambda *a, **kw: None,
        raising=False,
    )


@pytest.fixture
def keyring_fake(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """Explicit override for tests that exercise the real load_token code path.

    Overrides the autouse mock_keyring with a configurable MagicMock so the
    test can control the exact return value or side effect:

        def test_token_prefill(keyring_fake):
            keyring_fake.return_value = "secret"
            ...
    """
    fake: MagicMock = MagicMock(return_value=None)
    monkeypatch.setattr(
        "jwe.service.keyring.get_password",
        fake,
        raising=False,
    )
    return fake


@pytest.fixture
def isolated_settings(tmp_path: Path) -> QSettings:
    """IniFormat QSettings backed by a temp file — one per test, no OS registry writes."""
    return QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)


@pytest.fixture
def main_window(qtbot, isolated_settings: QSettings) -> Generator[MainWindow, None, None]:
    """MainWindow with isolated settings, registered with qtbot for cleanup."""
    w = MainWindow(_settings=isolated_settings)
    qtbot.addWidget(w)
    yield w
    w.close()  # triggers closeEvent, stopping all persistent threads cleanly


@pytest.fixture
def make_main_window(
    qtbot, isolated_settings: QSettings
) -> Generator[Any, None, None]:
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

    yield factory
    for w in _windows:
        w.close()  # triggers closeEvent, stopping all persistent threads cleanly
