"""Tests for StatusWidget -- Stage 4."""

from __future__ import annotations

import pytest

from jwe.gui.widgets.status import StatusWidget

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def widget(qtbot) -> StatusWidget:
    w = StatusWidget()
    qtbot.addWidget(w)
    return w


# ---------------------------------------------------------------------------
# Field presence
# ---------------------------------------------------------------------------


class TestFieldPresence:
    def test_has_export_btn(self, widget: StatusWidget) -> None:
        assert hasattr(widget, "export_btn")

    def test_has_status_label(self, widget: StatusWidget) -> None:
        assert hasattr(widget, "status_label")


# ---------------------------------------------------------------------------
# Initial state
# ---------------------------------------------------------------------------


class TestInitialState:
    def test_export_btn_disabled_by_default(self, widget: StatusWidget) -> None:
        assert not widget.export_btn.isEnabled()

    def test_status_label_has_initial_text(self, widget: StatusWidget) -> None:
        assert widget.status_label.text() != ""


# ---------------------------------------------------------------------------
# set_export_enabled
# ---------------------------------------------------------------------------


class TestSetExportEnabled:
    def test_set_true_enables_btn(self, widget: StatusWidget) -> None:
        widget.set_export_enabled(True)
        assert widget.export_btn.isEnabled()

    def test_set_false_disables_btn(self, widget: StatusWidget) -> None:
        widget.set_export_enabled(True)
        widget.set_export_enabled(False)
        assert not widget.export_btn.isEnabled()


# ---------------------------------------------------------------------------
# set_status_text
# ---------------------------------------------------------------------------


class TestSetStatusText:
    def test_updates_label(self, widget: StatusWidget) -> None:
        widget.set_status_text("Ready to export")
        assert widget.status_label.text() == "Ready to export"
