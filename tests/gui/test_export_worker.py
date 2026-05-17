"""Tests for ExportWorker -- Etappe 5a."""

from __future__ import annotations

import threading
from collections.abc import Iterator

import pytest

from jwe.config import ExportConfig
from jwe.exporter import ExportProgress, ExportResult
from jwe.gui.workers.export_worker import ExportWorker

# Minimal config -- run_fn is always mocked, so fields don't matter.
_MINIMAL_CONFIG = ExportConfig()

_RESULT_ZERO = ExportResult(
    issues_seen=0,
    worklogs_written=0,
    total_time_spent_seconds=0,
    output_path=None,
)


def _make_worker(
    events: list[ExportProgress | ExportResult],
    cancel_event: threading.Event | None = None,
) -> ExportWorker:
    """Return an ExportWorker whose run_fn yields *events* in order."""
    ce = cancel_event if cancel_event is not None else threading.Event()

    def run_fn(
        config: ExportConfig, ev: threading.Event
    ) -> Iterator[ExportProgress | ExportResult]:
        yield from events

    return ExportWorker(_MINIMAL_CONFIG, run_fn, ce)


# ---------------------------------------------------------------------------
# W-1 / W-2 / W-3: progress_updated and log_message
# ---------------------------------------------------------------------------


class TestProgressUpdated:
    def test_emits_for_each_progress_event(self, qtbot) -> None:
        received: list[tuple[int, int]] = []
        events: list[ExportProgress | ExportResult] = [
            ExportProgress(issues_seen=5, worklogs_written=10),
            ExportProgress(issues_seen=8, worklogs_written=15),
            ExportResult(
                issues_seen=8,
                worklogs_written=15,
                total_time_spent_seconds=0,
                output_path="/out.csv",
            ),
        ]
        worker = _make_worker(events)
        worker.progress_updated.connect(lambda i, w: received.append((i, w)))
        worker.run()
        assert received == [(5, 10), (8, 15)]

    def test_no_emission_when_no_progress_events(self, qtbot) -> None:
        received: list[tuple[int, int]] = []
        worker = _make_worker([_RESULT_ZERO])
        worker.progress_updated.connect(lambda i, w: received.append((i, w)))
        worker.run()
        assert received == []


class TestLogMessage:
    def test_emits_log_message_when_message_non_empty(self, qtbot) -> None:
        received: list[str] = []
        events: list[ExportProgress | ExportResult] = [
            ExportProgress(issues_seen=1, worklogs_written=0, message="Export complete."),
            _RESULT_ZERO,
        ]
        worker = _make_worker(events)
        worker.log_message.connect(received.append)
        worker.run()
        assert received == ["Export complete."]

    def test_no_log_message_when_message_empty(self, qtbot) -> None:
        received: list[str] = []
        events: list[ExportProgress | ExportResult] = [
            ExportProgress(issues_seen=1, worklogs_written=0, message=""),
            _RESULT_ZERO,
        ]
        worker = _make_worker(events)
        worker.log_message.connect(received.append)
        worker.run()
        assert received == []


# ---------------------------------------------------------------------------
# W-4 / W-5: finished signal
# ---------------------------------------------------------------------------


class TestFinished:
    def test_emits_finished_with_output_path(self, qtbot) -> None:
        received: list[str] = []
        events: list[ExportProgress | ExportResult] = [
            ExportResult(
                issues_seen=3,
                worklogs_written=7,
                total_time_spent_seconds=3600,
                output_path="/tmp/out.csv",
            )
        ]
        worker = _make_worker(events)
        worker.finished.connect(received.append)
        worker.run()
        assert received == ["/tmp/out.csv"]

    def test_emits_finished_with_empty_string_for_dry_run(self, qtbot) -> None:
        received: list[str] = []
        worker = _make_worker([_RESULT_ZERO])
        worker.finished.connect(received.append)
        worker.run()
        assert received == [""]

    def test_no_finished_when_exception_raised(self, qtbot) -> None:
        received: list[str] = []

        def run_fn(
            config: ExportConfig, ev: threading.Event
        ) -> Iterator[ExportProgress | ExportResult]:
            raise RuntimeError("network timeout")
            yield  # make it a generator

        worker = ExportWorker(_MINIMAL_CONFIG, run_fn, threading.Event())
        worker.finished.connect(received.append)
        worker.run()
        assert received == []


# ---------------------------------------------------------------------------
# W-6 / W-7: failed signal
# ---------------------------------------------------------------------------


class TestFailed:
    def test_emits_failed_on_immediate_exception(self, qtbot) -> None:
        received: list[str] = []

        def run_fn(
            config: ExportConfig, ev: threading.Event
        ) -> Iterator[ExportProgress | ExportResult]:
            raise RuntimeError("network timeout")
            yield

        worker = ExportWorker(_MINIMAL_CONFIG, run_fn, threading.Event())
        worker.failed.connect(received.append)
        worker.run()
        assert received == ["network timeout"]

    def test_emits_failed_on_mid_generator_exception(self, qtbot) -> None:
        received: list[str] = []

        def run_fn(
            config: ExportConfig, ev: threading.Event
        ) -> Iterator[ExportProgress | ExportResult]:
            yield ExportProgress(issues_seen=1, worklogs_written=0)
            raise RuntimeError("mid-run failure")

        worker = ExportWorker(_MINIMAL_CONFIG, run_fn, threading.Event())
        worker.failed.connect(received.append)
        worker.run()
        assert received == ["mid-run failure"]

    def test_no_failed_on_success(self, qtbot) -> None:
        received: list[str] = []
        worker = _make_worker([_RESULT_ZERO])
        worker.failed.connect(received.append)
        worker.run()
        assert received == []


# ---------------------------------------------------------------------------
# W-8: empty generator (only ExportResult, no ExportProgress)
# ---------------------------------------------------------------------------


class TestEmptyGenerator:
    def test_finished_with_zero_path_on_empty_generator(self, qtbot) -> None:
        finished: list[str] = []
        progress: list[tuple[int, int]] = []
        worker = _make_worker([_RESULT_ZERO])
        worker.finished.connect(finished.append)
        worker.progress_updated.connect(lambda i, w: progress.append((i, w)))
        worker.run()
        assert finished == [""]
        assert progress == []


# ---------------------------------------------------------------------------
# W-9 / W-10: cancel_event
# ---------------------------------------------------------------------------


class TestCancelEvent:
    def test_cancel_event_accepted_as_constructor_arg(self, qtbot) -> None:
        ce = threading.Event()
        worker = ExportWorker(_MINIMAL_CONFIG, lambda c, e: iter([_RESULT_ZERO]), ce)
        assert worker._cancel_event is ce

    def test_cancel_event_passed_to_run_fn(self, qtbot) -> None:
        received: list[threading.Event] = []

        def capturing_fn(
            config: ExportConfig, ev: threading.Event
        ) -> Iterator[ExportProgress | ExportResult]:
            received.append(ev)
            yield _RESULT_ZERO

        ce = threading.Event()
        worker = ExportWorker(_MINIMAL_CONFIG, capturing_fn, ce)
        worker.run()
        assert received == [ce]

    def test_cancel_event_not_set_by_worker_itself(self, qtbot) -> None:
        ce = threading.Event()
        worker = _make_worker([_RESULT_ZERO], cancel_event=ce)
        worker.run()
        assert not ce.is_set()
