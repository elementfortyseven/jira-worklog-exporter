"""Tests for StatusWidget -- Stage 5b additions (cancel button + result buttons)."""

from __future__ import annotations

import pytest

from jwe.gui.widgets.status import StatusWidget


@pytest.fixture
def widget(qtbot) -> StatusWidget:
    w = StatusWidget()
    qtbot.addWidget(w)
    w.show()
    qtbot.waitExposed(w)
    return w


# ---------------------------------------------------------------------------
# T04 / T05 / T06 / T07: cancel_btn presence and initial visibility
# ---------------------------------------------------------------------------


class TestCancelButtonPresence:
    def test_cancel_btn_exists(self, widget: StatusWidget) -> None:
        assert hasattr(widget, "cancel_btn")

    def test_cancel_btn_hidden_initially(self, widget: StatusWidget) -> None:
        assert not widget.cancel_btn.isVisible()

    def test_cancel_btn_visible_after_start_progress_display(
        self, widget: StatusWidget
    ) -> None:
        widget.start_progress_display()
        assert widget.cancel_btn.isVisible()

    def test_cancel_btn_not_visible_before_start_progress_display(
        self, widget: StatusWidget
    ) -> None:
        # Never called start_progress_display -- button must remain hidden.
        assert not widget.cancel_btn.isVisible()


# ---------------------------------------------------------------------------
# T08 / T09: disable_cancel_btn
# ---------------------------------------------------------------------------


class TestDisableCancelBtn:
    def test_cancel_btn_disabled_after_disable_cancel_btn(
        self, widget: StatusWidget
    ) -> None:
        widget.start_progress_display()
        widget.disable_cancel_btn()
        assert not widget.cancel_btn.isEnabled()

    def test_cancel_btn_not_disabled_before_disable(
        self, widget: StatusWidget
    ) -> None:
        widget.start_progress_display()
        # disable_cancel_btn not called -- button must still be enabled.
        assert widget.cancel_btn.isEnabled()


# ---------------------------------------------------------------------------
# T10 / T11: hide_cancel_btn and stop_progress_display
# ---------------------------------------------------------------------------


class TestHideCancelBtn:
    def test_cancel_btn_hidden_after_hide_cancel_btn(
        self, widget: StatusWidget
    ) -> None:
        widget.start_progress_display()
        widget.hide_cancel_btn()
        assert not widget.cancel_btn.isVisible()

    def test_cancel_btn_hidden_after_stop_progress_display(
        self, widget: StatusWidget
    ) -> None:
        widget.start_progress_display()
        widget.stop_progress_display()
        assert not widget.cancel_btn.isVisible()


# ---------------------------------------------------------------------------
# T12 / T13: cancel_requested signal
# ---------------------------------------------------------------------------


class TestCancelRequestedSignal:
    def test_cancel_requested_signal_emitted_on_btn_click(
        self, widget: StatusWidget, qtbot
    ) -> None:
        widget.start_progress_display()
        received: list[bool] = []
        widget.cancel_requested.connect(lambda: received.append(True))

        widget.cancel_btn.click()

        assert received == [True]

    def test_cancel_requested_not_emitted_without_click(
        self, widget: StatusWidget
    ) -> None:
        received: list[bool] = []
        widget.cancel_requested.connect(lambda: received.append(True))

        # No click -- signal must not have fired.
        assert received == []


# ---------------------------------------------------------------------------
# T14 / T15 / T16: result row and button presence
# ---------------------------------------------------------------------------


class TestResultRowPresence:
    def test_result_row_exists(self, widget: StatusWidget) -> None:
        assert hasattr(widget, "_result_row")

    def test_open_csv_btn_exists(self, widget: StatusWidget) -> None:
        assert hasattr(widget, "open_csv_btn")

    def test_open_folder_btn_exists(self, widget: StatusWidget) -> None:
        assert hasattr(widget, "open_folder_btn")


# ---------------------------------------------------------------------------
# T17 / T18 / T19: result row visibility
# ---------------------------------------------------------------------------


class TestResultRowVisibility:
    def test_result_row_hidden_initially(self, widget: StatusWidget) -> None:
        assert not widget._result_row.isVisible()

    def test_result_row_visible_after_show_result_buttons(
        self, widget: StatusWidget
    ) -> None:
        widget.show_result_buttons("/tmp/out.csv")
        assert widget._result_row.isVisible()

    def test_result_row_hidden_when_not_shown(self, widget: StatusWidget) -> None:
        # show_result_buttons never called -- row must stay hidden.
        assert not widget._result_row.isVisible()


# ---------------------------------------------------------------------------
# T20 / T21: result row hidden by lifecycle methods
# ---------------------------------------------------------------------------


class TestResultRowHiddenByLifecycle:
    def test_result_row_hidden_after_stop_progress_display(
        self, widget: StatusWidget
    ) -> None:
        widget.show_result_buttons("/tmp/out.csv")
        widget.stop_progress_display()
        assert not widget._result_row.isVisible()

    def test_result_row_hidden_after_start_progress_display(
        self, widget: StatusWidget
    ) -> None:
        widget.show_result_buttons("/tmp/out.csv")
        widget.start_progress_display()
        assert not widget._result_row.isVisible()
