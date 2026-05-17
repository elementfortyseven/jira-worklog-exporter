"""Tests for StatusWidget -- Etappe 5a additions (progress display)."""

from __future__ import annotations

import pytest

from jwe.gui.widgets.status import StatusWidget


@pytest.fixture
def widget(qtbot) -> StatusWidget:
    w = StatusWidget()
    qtbot.addWidget(w)
    w.show()
    return w


# ---------------------------------------------------------------------------
# S-1 to S-4: field presence
# ---------------------------------------------------------------------------


class TestFieldPresence:
    def test_has_progress_bar(self, widget: StatusWidget) -> None:
        assert hasattr(widget, "progress_bar")

    def test_has_issue_label(self, widget: StatusWidget) -> None:
        assert hasattr(widget, "issue_label")

    def test_has_worklog_label(self, widget: StatusWidget) -> None:
        assert hasattr(widget, "worklog_label")

    def test_has_log_panel(self, widget: StatusWidget) -> None:
        assert hasattr(widget, "log_panel")

    def test_log_panel_is_read_only(self, widget: StatusWidget) -> None:
        assert widget.log_panel.isReadOnly()


# ---------------------------------------------------------------------------
# S-5 / S-7 / S-9: initial hidden state
# ---------------------------------------------------------------------------


class TestInitialHiddenState:
    def test_progress_bar_hidden_initially(self, widget: StatusWidget) -> None:
        assert not widget.progress_bar.isVisible()

    def test_counter_row_hidden_initially(self, widget: StatusWidget) -> None:
        assert not widget._counter_row.isVisible()

    def test_log_panel_hidden_initially(self, widget: StatusWidget) -> None:
        assert not widget.log_panel.isVisible()


# ---------------------------------------------------------------------------
# S-6 / S-8 / S-10: visible after start_progress_display
# ---------------------------------------------------------------------------


class TestStartProgressDisplay:
    def test_progress_bar_visible_after_start(self, widget: StatusWidget) -> None:
        widget.start_progress_display()
        assert widget.progress_bar.isVisible()

    def test_counter_row_visible_after_start(self, widget: StatusWidget) -> None:
        widget.start_progress_display()
        assert widget._counter_row.isVisible()

    def test_log_panel_visible_after_start(self, widget: StatusWidget) -> None:
        widget.start_progress_display()
        assert widget.log_panel.isVisible()

    def test_progress_bar_is_indeterminate_after_start(self, widget: StatusWidget) -> None:
        widget.start_progress_display()
        assert widget.progress_bar.maximum() == 0

    def test_log_panel_cleared_on_repeated_start(self, widget: StatusWidget) -> None:
        widget.start_progress_display()
        widget.append_log_line("leftover")
        widget.stop_progress_display()
        widget.start_progress_display()
        assert widget.log_panel.toPlainText() == ""


# ---------------------------------------------------------------------------
# S-16: stop_progress_display hides everything
# ---------------------------------------------------------------------------


class TestStopProgressDisplay:
    def test_progress_bar_hidden_after_stop(self, widget: StatusWidget) -> None:
        widget.start_progress_display()
        widget.stop_progress_display()
        assert not widget.progress_bar.isVisible()

    def test_counter_row_hidden_after_stop(self, widget: StatusWidget) -> None:
        widget.start_progress_display()
        widget.stop_progress_display()
        assert not widget._counter_row.isVisible()

    def test_log_panel_hidden_after_stop(self, widget: StatusWidget) -> None:
        widget.start_progress_display()
        widget.stop_progress_display()
        assert not widget.log_panel.isVisible()


# ---------------------------------------------------------------------------
# on_progress_done: stops marquee but keeps counter and log visible
# ---------------------------------------------------------------------------


class TestOnProgressDone:
    def test_progress_bar_stops_marquee(self, widget: StatusWidget) -> None:
        widget.start_progress_display()
        assert widget.progress_bar.maximum() == 0  # marquee active
        widget.on_progress_done()
        assert widget.progress_bar.maximum() != 0  # marquee stopped

    def test_counter_row_still_visible_after_done(self, widget: StatusWidget) -> None:
        widget.start_progress_display()
        widget.on_progress_done()
        assert widget._counter_row.isVisible()

    def test_log_panel_still_visible_after_done(self, widget: StatusWidget) -> None:
        widget.start_progress_display()
        widget.on_progress_done()
        assert widget.log_panel.isVisible()

    def test_progress_bar_still_visible_after_done(self, widget: StatusWidget) -> None:
        widget.start_progress_display()
        widget.on_progress_done()
        assert widget.progress_bar.isVisible()


# ---------------------------------------------------------------------------
# S-11 / S-12: on_progress_updated updates counter labels
# ---------------------------------------------------------------------------


class TestOnProgressUpdated:
    def test_issue_label_shows_count(self, widget: StatusWidget) -> None:
        widget.start_progress_display()
        widget.on_progress_updated(5, 12)
        assert "5" in widget.issue_label.text()

    def test_worklog_label_shows_count(self, widget: StatusWidget) -> None:
        widget.start_progress_display()
        widget.on_progress_updated(5, 12)
        assert "12" in widget.worklog_label.text()

    def test_zero_counts_displayed(self, widget: StatusWidget) -> None:
        widget.start_progress_display()
        widget.on_progress_updated(0, 0)
        assert "0" in widget.issue_label.text()
        assert "0" in widget.worklog_label.text()

    def test_large_counts_displayed(self, widget: StatusWidget) -> None:
        widget.start_progress_display()
        widget.on_progress_updated(999, 12345)
        assert "999" in widget.issue_label.text()
        assert "12345" in widget.worklog_label.text()


# ---------------------------------------------------------------------------
# S-13 / S-14 / S-15: append_log_line and 50-line cap
# ---------------------------------------------------------------------------


class TestAppendLogLine:
    def test_single_line_present_in_log(self, widget: StatusWidget) -> None:
        widget.start_progress_display()
        widget.append_log_line("hello world")
        assert "hello world" in widget.log_panel.toPlainText()

    def test_multiple_lines_all_present_below_limit(self, widget: StatusWidget) -> None:
        widget.start_progress_display()
        widget.append_log_line("line A")
        widget.append_log_line("line B")
        text = widget.log_panel.toPlainText()
        assert "line A" in text
        assert "line B" in text

    def test_exactly_49_lines_all_kept(self, widget: StatusWidget) -> None:
        widget.start_progress_display()
        for i in range(49):
            widget.append_log_line(f"entry {i}")
        lines = widget.log_panel.toPlainText().splitlines()
        assert len(lines) == 49

    def test_exactly_50_lines_all_kept(self, widget: StatusWidget) -> None:
        widget.start_progress_display()
        for i in range(50):
            widget.append_log_line(f"entry {i}")
        lines = widget.log_panel.toPlainText().splitlines()
        assert len(lines) == 50

    def test_60_lines_capped_at_50(self, widget: StatusWidget) -> None:
        widget.start_progress_display()
        for i in range(60):
            widget.append_log_line(f"entry {i}")
        lines = widget.log_panel.toPlainText().splitlines()
        assert len(lines) <= 50

    def test_oldest_lines_dropped_when_over_limit(self, widget: StatusWidget) -> None:
        widget.start_progress_display()
        for i in range(60):
            widget.append_log_line(f"entry {i}")
        text = widget.log_panel.toPlainText()
        assert "entry 0" not in text
        assert "entry 59" in text


# ---------------------------------------------------------------------------
# Result-display mode: counter and log stay visible after on_progress_done
# ---------------------------------------------------------------------------


class TestResultDisplayMode:
    def test_counter_visible_after_done_with_final_values(
        self, widget: StatusWidget
    ) -> None:
        widget.start_progress_display()
        widget.on_progress_updated(5, 12)
        widget.on_progress_done()
        assert widget._counter_row.isVisible()
        assert "5" in widget.issue_label.text()
        assert "12" in widget.worklog_label.text()

    def test_log_visible_after_done_with_final_message(
        self, widget: StatusWidget
    ) -> None:
        widget.start_progress_display()
        widget.append_log_line("Export complete. Output: /tmp/out.csv")
        widget.on_progress_done()
        assert widget.log_panel.isVisible()
        assert "Export complete" in widget.log_panel.toPlainText()

    def test_progress_bar_stopped_after_done(self, widget: StatusWidget) -> None:
        widget.start_progress_display()
        widget.on_progress_done()
        assert widget.progress_bar.maximum() != 0
