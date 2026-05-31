"""Tests for UserSearchWorker (Pattern C -- persistent worker, JWE-26)."""

from __future__ import annotations

from unittest.mock import MagicMock

from jwe.api.user import User
from jwe.gui.workers.user_search import UserSearchWorker

_ALICE = User(account_id="acc-alice", display_name="Alice Smith", email="alice@example.com", active=True)
_BOB = User(account_id="acc-bob", display_name="Bob Jones", email="bob@example.com", active=True)


# ---------------------------------------------------------------------------
# Signals presence
# ---------------------------------------------------------------------------


class TestSignals:
    def test_results_signal_exists(self) -> None:
        worker = UserSearchWorker()
        assert hasattr(worker, "results")

    def test_failed_signal_exists(self) -> None:
        worker = UserSearchWorker()
        assert hasattr(worker, "failed")

    def test_query_requested_signal_exists(self) -> None:
        worker = UserSearchWorker()
        assert hasattr(worker, "query_requested")


# ---------------------------------------------------------------------------
# Initialisation
# ---------------------------------------------------------------------------


class TestInit:
    def test_instantiates_without_args(self) -> None:
        worker = UserSearchWorker()
        assert worker is not None

    def test_search_fn_initially_none(self) -> None:
        worker = UserSearchWorker()
        assert worker._search_fn is None

    def test_query_requested_connected_to_on_query_requested(self, qtbot) -> None:
        worker = UserSearchWorker()
        fn = MagicMock(return_value=[])
        worker.set_search_fn(fn)
        # Emitting the signal should trigger _on_query_requested via the connection
        with qtbot.waitSignal(worker.results, timeout=1000):
            worker.query_requested.emit("hello")


# ---------------------------------------------------------------------------
# set_search_fn
# ---------------------------------------------------------------------------


class TestSetSearchFn:
    def test_stores_callable(self) -> None:
        worker = UserSearchWorker()
        fn = MagicMock(return_value=[])
        worker.set_search_fn(fn)
        assert worker._search_fn is fn

    def test_none_clears_fn(self) -> None:
        worker = UserSearchWorker()
        worker.set_search_fn(MagicMock())
        worker.set_search_fn(None)
        assert worker._search_fn is None

    def test_replaces_previous_fn(self) -> None:
        worker = UserSearchWorker()
        fn1 = MagicMock(return_value=[])
        fn2 = MagicMock(return_value=[])
        worker.set_search_fn(fn1)
        worker.set_search_fn(fn2)
        assert worker._search_fn is fn2


# ---------------------------------------------------------------------------
# _on_query_requested -- slot behaviour (called directly, no thread needed)
# ---------------------------------------------------------------------------


class TestOnQueryRequested:
    def test_emits_results_when_fn_set(self, qtbot) -> None:
        worker = UserSearchWorker()
        worker.set_search_fn(MagicMock(return_value=[_ALICE]))
        with qtbot.waitSignal(worker.results, timeout=1000) as blocker:
            worker._on_query_requested("alice")
        assert blocker.args[0] == [_ALICE]

    def test_results_contain_all_returned_users(self, qtbot) -> None:
        worker = UserSearchWorker()
        worker.set_search_fn(MagicMock(return_value=[_ALICE, _BOB]))
        with qtbot.waitSignal(worker.results, timeout=1000) as blocker:
            worker._on_query_requested("a")
        assert blocker.args[0] == [_ALICE, _BOB]

    def test_fn_called_with_exact_query(self, qtbot) -> None:
        worker = UserSearchWorker()
        fn = MagicMock(return_value=[])
        worker.set_search_fn(fn)
        with qtbot.waitSignal(worker.results, timeout=1000):
            worker._on_query_requested("specific query")
        fn.assert_called_once_with("specific query")

    def test_emits_failed_when_fn_none(self, qtbot) -> None:
        worker = UserSearchWorker()
        # fn is None (default)
        with qtbot.waitSignal(worker.failed, timeout=1000) as blocker:
            worker._on_query_requested("alice")
        assert "Authentication required" in blocker.args[0]

    def test_does_not_emit_results_when_fn_none(self, qtbot) -> None:
        worker = UserSearchWorker()
        received: list[object] = []
        worker.results.connect(received.append)
        with qtbot.waitSignal(worker.failed, timeout=1000):
            worker._on_query_requested("alice")
        assert received == []

    def test_emits_failed_on_exception(self, qtbot) -> None:
        worker = UserSearchWorker()
        worker.set_search_fn(MagicMock(side_effect=Exception("network error")))
        with qtbot.waitSignal(worker.failed, timeout=1000) as blocker:
            worker._on_query_requested("alice")
        assert "network error" in blocker.args[0]

    def test_does_not_emit_results_on_exception(self, qtbot) -> None:
        worker = UserSearchWorker()
        worker.set_search_fn(MagicMock(side_effect=Exception("network error")))
        received: list[object] = []
        worker.results.connect(received.append)
        with qtbot.waitSignal(worker.failed, timeout=1000):
            worker._on_query_requested("alice")
        assert received == []

    def test_emits_results_not_failed_on_empty_result(self, qtbot) -> None:
        worker = UserSearchWorker()
        worker.set_search_fn(MagicMock(return_value=[]))
        failed_received: list[str] = []
        worker.failed.connect(failed_received.append)
        with qtbot.waitSignal(worker.results, timeout=1000) as blocker:
            worker._on_query_requested("xyz")
        assert blocker.args[0] == []
        assert failed_received == []
