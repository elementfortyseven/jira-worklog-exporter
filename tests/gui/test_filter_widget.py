"""Tests for FilterWidget -- Etappe 4."""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtCore import QDate, QSettings

from jwe.gui.widgets.filter import FilterWidget

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def widget(qtbot) -> FilterWidget:
    w = FilterWidget()
    qtbot.addWidget(w)
    return w


@pytest.fixture
def isolated_settings(tmp_path: Path) -> QSettings:
    return QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)


# ---------------------------------------------------------------------------
# Field presence
# ---------------------------------------------------------------------------


class TestFieldPresence:
    def test_has_from_date_field(self, widget: FilterWidget) -> None:
        assert hasattr(widget, "from_date")

    def test_has_to_date_field(self, widget: FilterWidget) -> None:
        assert hasattr(widget, "to_date")

    def test_has_project_keys_field(self, widget: FilterWidget) -> None:
        assert hasattr(widget, "project_keys_field")


# ---------------------------------------------------------------------------
# Default values
# ---------------------------------------------------------------------------


class TestDefaultValues:
    def test_from_date_default_is_first_of_current_month(self, widget: FilterWidget) -> None:
        today = QDate.currentDate()
        expected = QDate(today.year(), today.month(), 1)
        assert widget.from_date.date() == expected

    def test_to_date_default_is_last_of_current_month(self, widget: FilterWidget) -> None:
        today = QDate.currentDate()
        first = QDate(today.year(), today.month(), 1)
        expected = first.addMonths(1).addDays(-1)
        assert widget.to_date.date() == expected

    def test_project_keys_default_is_empty(self, widget: FilterWidget) -> None:
        assert widget.project_keys_field.text() == ""


# ---------------------------------------------------------------------------
# is_valid -- date logic
# ---------------------------------------------------------------------------


class TestIsValidDates:
    def test_valid_when_from_equals_to(self, widget: FilterWidget) -> None:
        today = QDate.currentDate()
        widget.from_date.setDate(today)
        widget.to_date.setDate(today)
        assert widget.is_valid() is True

    def test_valid_when_from_lt_to(self, widget: FilterWidget) -> None:
        widget.from_date.setDate(QDate(2026, 1, 1))
        widget.to_date.setDate(QDate(2026, 1, 31))
        assert widget.is_valid() is True

    def test_invalid_when_from_gt_to(self, widget: FilterWidget) -> None:
        widget.from_date.setDate(QDate(2026, 2, 1))
        widget.to_date.setDate(QDate(2026, 1, 31))
        assert widget.is_valid() is False

    def test_valid_after_correcting_inverted_range(self, widget: FilterWidget) -> None:
        widget.from_date.setDate(QDate(2026, 2, 1))
        widget.to_date.setDate(QDate(2026, 1, 31))
        assert widget.is_valid() is False
        widget.from_date.setDate(QDate(2026, 1, 1))
        assert widget.is_valid() is True


# ---------------------------------------------------------------------------
# is_valid -- project keys
# ---------------------------------------------------------------------------


class TestIsValidProjectKeys:
    def test_valid_when_project_keys_empty(self, widget: FilterWidget) -> None:
        widget.project_keys_field.setText("")
        assert widget.is_valid() is True

    def test_valid_with_single_valid_key(self, widget: FilterWidget) -> None:
        widget.project_keys_field.setText("PROJ")
        assert widget.is_valid() is True

    def test_valid_with_multiple_valid_keys(self, widget: FilterWidget) -> None:
        widget.project_keys_field.setText("PROJ, SUPP")
        assert widget.is_valid() is True

    def test_valid_with_underscore_in_key(self, widget: FilterWidget) -> None:
        widget.project_keys_field.setText("MY_PROJECT")
        assert widget.is_valid() is True

    def test_invalid_when_key_is_lowercase(self, widget: FilterWidget) -> None:
        widget.project_keys_field.setText("proj")
        assert widget.is_valid() is False

    def test_invalid_when_key_starts_with_digit(self, widget: FilterWidget) -> None:
        widget.project_keys_field.setText("1PROJ")
        assert widget.is_valid() is False

    def test_invalid_when_key_contains_hyphen(self, widget: FilterWidget) -> None:
        widget.project_keys_field.setText("MY-PROJECT")
        assert widget.is_valid() is False

    def test_invalid_when_one_key_in_list_is_bad(self, widget: FilterWidget) -> None:
        widget.project_keys_field.setText("PROJ, bad")
        assert widget.is_valid() is False


# ---------------------------------------------------------------------------
# validation_changed signal
# ---------------------------------------------------------------------------


class TestValidationChangedSignal:
    def test_emitted_on_to_date_change(self, qtbot, widget: FilterWidget) -> None:
        with qtbot.waitSignal(widget.validation_changed, timeout=500):
            widget.to_date.setDate(QDate(2026, 6, 30))

    def test_emitted_on_from_date_change(self, qtbot, widget: FilterWidget) -> None:
        with qtbot.waitSignal(widget.validation_changed, timeout=500):
            widget.from_date.setDate(QDate(2026, 6, 1))

    def test_emitted_on_project_keys_change(self, qtbot, widget: FilterWidget) -> None:
        with qtbot.waitSignal(widget.validation_changed, timeout=500):
            widget.project_keys_field.setText("PROJ")


# ---------------------------------------------------------------------------
# QSettings
# ---------------------------------------------------------------------------


class TestQSettings:
    def test_project_keys_roundtrip(
        self, widget: FilterWidget, isolated_settings: QSettings
    ) -> None:
        widget.project_keys_field.setText("PROJ, SUPP")
        widget.save_settings(isolated_settings)
        widget.project_keys_field.setText("")
        widget.load_settings(isolated_settings)
        assert widget.project_keys_field.text() == "PROJ, SUPP"

    def test_from_date_not_saved(
        self, widget: FilterWidget, isolated_settings: QSettings
    ) -> None:
        widget.from_date.setDate(QDate(2026, 3, 1))
        widget.save_settings(isolated_settings)
        assert isolated_settings.value("filter/from_date") is None

    def test_to_date_not_saved(
        self, widget: FilterWidget, isolated_settings: QSettings
    ) -> None:
        widget.to_date.setDate(QDate(2026, 3, 31))
        widget.save_settings(isolated_settings)
        assert isolated_settings.value("filter/to_date") is None
