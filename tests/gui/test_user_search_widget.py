"""Tests for UserSearchWidget and UserSearchWorker -- Etappe 3."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import QListWidgetItem

from jwe.api.user import User
from jwe.gui.widgets.user_search import UserSearchWidget

# ---------------------------------------------------------------------------
# Fake data
# ---------------------------------------------------------------------------

_ALICE = User(account_id="acc-alice", display_name="Alice Smith", email="alice@example.com", active=True)
_BOB = User(account_id="acc-bob", display_name="Bob Jones", email="bob@example.com", active=True)
_CAROL = User(account_id="acc-carol", display_name="Carol White", email="carol@example.com", active=True)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_search_fn() -> MagicMock:
    return MagicMock(return_value=[])


@pytest.fixture
def widget(qtbot, mock_search_fn: MagicMock) -> UserSearchWidget:
    w = UserSearchWidget(search_fn=mock_search_fn)
    qtbot.addWidget(w)
    return w


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _populate_results(w: UserSearchWidget, users: list[User]) -> None:
    """Populate results_list directly, bypassing debounce/worker."""
    w._on_search_results(users)


def _add_to_selected(w: UserSearchWidget, user: User) -> None:
    """Add a user directly to selected_list, bypassing shuttle logic."""
    item = QListWidgetItem(f"{user.display_name}\n{user.email}")
    item.setData(Qt.ItemDataRole.UserRole, user.account_id)
    item.setSizeHint(QSize(-1, 44))
    w.selected_list.addItem(item)


# ---------------------------------------------------------------------------
# Layout presence
# ---------------------------------------------------------------------------


class TestLayoutPresence:
    def test_has_search_field(self, widget: UserSearchWidget) -> None:
        assert hasattr(widget, "search_field")
        from PySide6.QtWidgets import QLineEdit
        assert isinstance(widget.search_field, QLineEdit)

    def test_has_results_list(self, widget: UserSearchWidget) -> None:
        assert hasattr(widget, "results_list")
        from PySide6.QtWidgets import QListWidget
        assert isinstance(widget.results_list, QListWidget)

    def test_has_selected_list(self, widget: UserSearchWidget) -> None:
        assert hasattr(widget, "selected_list")
        from PySide6.QtWidgets import QListWidget
        assert isinstance(widget.selected_list, QListWidget)

    def test_has_btn_add_one(self, widget: UserSearchWidget) -> None:
        assert hasattr(widget, "btn_add_one")
        assert widget.btn_add_one.text() == ">"

    def test_has_btn_add_all(self, widget: UserSearchWidget) -> None:
        assert hasattr(widget, "btn_add_all")
        assert widget.btn_add_all.text() == ">>"

    def test_has_btn_rem_one(self, widget: UserSearchWidget) -> None:
        assert hasattr(widget, "btn_rem_one")
        assert widget.btn_rem_one.text() == "<"

    def test_has_btn_rem_all(self, widget: UserSearchWidget) -> None:
        assert hasattr(widget, "btn_rem_all")
        assert widget.btn_rem_all.text() == "<<"

    def test_has_search_status_label(self, widget: UserSearchWidget) -> None:
        assert hasattr(widget, "search_status_label")
        from PySide6.QtWidgets import QLabel
        assert isinstance(widget.search_status_label, QLabel)


# ---------------------------------------------------------------------------
# Debounce
# ---------------------------------------------------------------------------


class TestDebounce:
    def test_typing_does_not_start_worker_immediately(
        self, widget: UserSearchWidget, mock_search_fn: MagicMock
    ) -> None:
        widget.search_field.setText("alice")
        assert widget._debounce_timer.isActive()
        mock_search_fn.assert_not_called()

    def test_worker_starts_after_400ms(
        self, qtbot, widget: UserSearchWidget, mock_search_fn: MagicMock
    ) -> None:
        mock_search_fn.return_value = []
        widget.search_field.setText("alice")
        qtbot.waitUntil(lambda: mock_search_fn.called, timeout=1500)
        mock_search_fn.assert_called_once_with("alice")

    def test_retyping_before_timeout_resets_timer(
        self, qtbot, widget: UserSearchWidget, mock_search_fn: MagicMock
    ) -> None:
        mock_search_fn.return_value = []
        widget.search_field.setText("ali")
        qtbot.wait(200)  # less than 400ms debounce
        assert not mock_search_fn.called
        widget.search_field.setText("alice")
        qtbot.waitUntil(lambda: mock_search_fn.called, timeout=1500)
        assert mock_search_fn.call_count == 1
        assert mock_search_fn.call_args[0][0] == "alice"

    def test_empty_text_stops_timer(
        self, widget: UserSearchWidget, mock_search_fn: MagicMock
    ) -> None:
        widget.search_field.setText("ali")
        assert widget._debounce_timer.isActive()
        widget.search_field.setText("")
        assert not widget._debounce_timer.isActive()

    def test_empty_text_no_worker_started(
        self, qtbot, widget: UserSearchWidget, mock_search_fn: MagicMock
    ) -> None:
        widget.search_field.setText("ali")
        widget.search_field.setText("")
        qtbot.wait(600)
        mock_search_fn.assert_not_called()

    def test_empty_text_clears_results_list(
        self, widget: UserSearchWidget
    ) -> None:
        # search_field starts empty; type text first so setText("") emits textChanged
        widget.search_field.setText("alice")
        _populate_results(widget, [_ALICE, _BOB])
        widget.search_field.setText("")
        assert widget.results_list.count() == 0


# ---------------------------------------------------------------------------
# Shuttle: add_one (>)
# ---------------------------------------------------------------------------


class TestShuttleAddOne:
    def test_add_one_moves_selected_item_to_right(
        self, qtbot, widget: UserSearchWidget
    ) -> None:
        _populate_results(widget, [_ALICE])
        widget.results_list.setCurrentRow(0)
        qtbot.mouseClick(widget.btn_add_one, Qt.MouseButton.LeftButton)
        assert widget.selected_list.count() == 1

    def test_add_one_removes_item_from_left(
        self, qtbot, widget: UserSearchWidget
    ) -> None:
        _populate_results(widget, [_ALICE])
        widget.results_list.setCurrentRow(0)
        qtbot.mouseClick(widget.btn_add_one, Qt.MouseButton.LeftButton)
        assert widget.results_list.count() == 0

    def test_add_one_with_no_selection_no_effect(
        self, qtbot, widget: UserSearchWidget
    ) -> None:
        _populate_results(widget, [_ALICE])
        widget.results_list.clearSelection()
        qtbot.mouseClick(widget.btn_add_one, Qt.MouseButton.LeftButton)
        assert widget.results_list.count() == 1
        assert widget.selected_list.count() == 0


# ---------------------------------------------------------------------------
# Shuttle: add_all (>>)
# ---------------------------------------------------------------------------


class TestShuttleAddAll:
    def test_add_all_moves_all_items_to_right(
        self, qtbot, widget: UserSearchWidget
    ) -> None:
        _populate_results(widget, [_ALICE, _BOB])
        qtbot.mouseClick(widget.btn_add_all, Qt.MouseButton.LeftButton)
        assert widget.selected_list.count() == 2

    def test_add_all_empties_left_list(
        self, qtbot, widget: UserSearchWidget
    ) -> None:
        _populate_results(widget, [_ALICE, _BOB])
        qtbot.mouseClick(widget.btn_add_all, Qt.MouseButton.LeftButton)
        assert widget.results_list.count() == 0

    def test_add_all_on_empty_left_no_effect(
        self, qtbot, widget: UserSearchWidget
    ) -> None:
        _add_to_selected(widget, _ALICE)
        assert widget.results_list.count() == 0
        qtbot.mouseClick(widget.btn_add_all, Qt.MouseButton.LeftButton)
        assert widget.selected_list.count() == 1


# ---------------------------------------------------------------------------
# Shuttle: rem_one (<)
# ---------------------------------------------------------------------------


class TestShuttleRemOne:
    def test_rem_one_removes_selected_from_right(
        self, qtbot, widget: UserSearchWidget
    ) -> None:
        _add_to_selected(widget, _ALICE)
        widget.selected_list.setCurrentRow(0)
        qtbot.mouseClick(widget.btn_rem_one, Qt.MouseButton.LeftButton)
        assert widget.selected_list.count() == 0

    def test_rem_one_does_not_add_to_left(
        self, qtbot, widget: UserSearchWidget
    ) -> None:
        _add_to_selected(widget, _ALICE)
        widget.selected_list.setCurrentRow(0)
        qtbot.mouseClick(widget.btn_rem_one, Qt.MouseButton.LeftButton)
        assert widget.results_list.count() == 0

    def test_rem_one_with_no_selection_no_effect(
        self, qtbot, widget: UserSearchWidget
    ) -> None:
        _add_to_selected(widget, _ALICE)
        widget.selected_list.clearSelection()
        qtbot.mouseClick(widget.btn_rem_one, Qt.MouseButton.LeftButton)
        assert widget.selected_list.count() == 1


# ---------------------------------------------------------------------------
# Shuttle: rem_all (<<)
# ---------------------------------------------------------------------------


class TestShuttleRemAll:
    def test_rem_all_clears_right_list(
        self, qtbot, widget: UserSearchWidget
    ) -> None:
        _add_to_selected(widget, _ALICE)
        _add_to_selected(widget, _BOB)
        qtbot.mouseClick(widget.btn_rem_all, Qt.MouseButton.LeftButton)
        assert widget.selected_list.count() == 0

    def test_rem_all_does_not_modify_left(
        self, qtbot, widget: UserSearchWidget
    ) -> None:
        _populate_results(widget, [_CAROL])
        _add_to_selected(widget, _ALICE)
        qtbot.mouseClick(widget.btn_rem_all, Qt.MouseButton.LeftButton)
        assert widget.results_list.count() == 1

    def test_rem_all_on_empty_right_no_effect(
        self, qtbot, widget: UserSearchWidget
    ) -> None:
        assert widget.selected_list.count() == 0
        # must not raise
        qtbot.mouseClick(widget.btn_rem_all, Qt.MouseButton.LeftButton)
        assert widget.selected_list.count() == 0


# ---------------------------------------------------------------------------
# Double-click shortcuts
# ---------------------------------------------------------------------------


class TestDoubleClick:
    def test_double_click_left_moves_to_right(
        self, widget: UserSearchWidget
    ) -> None:
        _populate_results(widget, [_ALICE])
        item = widget.results_list.item(0)
        assert item is not None
        widget.results_list.itemDoubleClicked.emit(item)
        assert widget.selected_list.count() == 1

    def test_double_click_left_removes_from_left(
        self, widget: UserSearchWidget
    ) -> None:
        _populate_results(widget, [_ALICE])
        item = widget.results_list.item(0)
        assert item is not None
        widget.results_list.itemDoubleClicked.emit(item)
        assert widget.results_list.count() == 0

    def test_double_click_right_removes_from_right(
        self, widget: UserSearchWidget
    ) -> None:
        _add_to_selected(widget, _ALICE)
        item = widget.selected_list.item(0)
        assert item is not None
        widget.selected_list.itemDoubleClicked.emit(item)
        assert widget.selected_list.count() == 0

    def test_double_click_right_does_not_add_to_left(
        self, widget: UserSearchWidget
    ) -> None:
        _add_to_selected(widget, _ALICE)
        item = widget.selected_list.item(0)
        assert item is not None
        widget.selected_list.itemDoubleClicked.emit(item)
        assert widget.results_list.count() == 0


# ---------------------------------------------------------------------------
# Duplicate guard
# ---------------------------------------------------------------------------


class TestDuplicateGuard:
    def test_add_one_duplicate_not_inserted(
        self, qtbot, widget: UserSearchWidget
    ) -> None:
        _add_to_selected(widget, _ALICE)
        _populate_results(widget, [_ALICE])
        widget.results_list.setCurrentRow(0)
        qtbot.mouseClick(widget.btn_add_one, Qt.MouseButton.LeftButton)
        assert widget.selected_list.count() == 1

    def test_add_all_skips_existing_in_right(
        self, qtbot, widget: UserSearchWidget
    ) -> None:
        _add_to_selected(widget, _ALICE)
        _populate_results(widget, [_ALICE, _BOB])
        qtbot.mouseClick(widget.btn_add_all, Qt.MouseButton.LeftButton)
        # _ALICE already in right, _BOB added: total 2, not 3
        assert widget.selected_list.count() == 2

    def test_add_all_with_duplicate_empties_left(
        self, qtbot, widget: UserSearchWidget
    ) -> None:
        _add_to_selected(widget, _ALICE)
        _populate_results(widget, [_ALICE, _BOB])
        qtbot.mouseClick(widget.btn_add_all, Qt.MouseButton.LeftButton)
        assert widget.results_list.count() == 0


# ---------------------------------------------------------------------------
# Worker results and failures
# ---------------------------------------------------------------------------


class TestWorkerResults:
    def test_worker_success_populates_results_list(
        self, qtbot, widget: UserSearchWidget, mock_search_fn: MagicMock
    ) -> None:
        mock_search_fn.return_value = [_ALICE, _BOB, _CAROL]
        widget.search_field.setText("a")
        qtbot.waitUntil(lambda: widget.results_list.count() == 3, timeout=1500)

    def test_worker_results_carry_account_id_as_user_role(
        self, qtbot, widget: UserSearchWidget, mock_search_fn: MagicMock
    ) -> None:
        mock_search_fn.return_value = [_ALICE]
        widget.search_field.setText("alice")
        qtbot.waitUntil(lambda: widget.results_list.count() == 1, timeout=1500)
        item = widget.results_list.item(0)
        assert item is not None
        assert item.data(Qt.ItemDataRole.UserRole) == "acc-alice"

    def test_worker_failure_shows_status_label(
        self, qtbot, widget: UserSearchWidget, mock_search_fn: MagicMock
    ) -> None:
        mock_search_fn.side_effect = Exception("network error")
        widget.search_field.setText("alice")
        qtbot.waitUntil(
            lambda: "network error" in widget.search_status_label.text(),
            timeout=1500,
        )
        assert "network error" in widget.search_status_label.text()

    def test_worker_failure_does_not_populate_results_list(
        self, qtbot, widget: UserSearchWidget, mock_search_fn: MagicMock
    ) -> None:
        mock_search_fn.side_effect = Exception("network error")
        widget.search_field.setText("alice")
        qtbot.waitUntil(
            lambda: bool(widget.search_status_label.text()), timeout=1500
        )
        assert widget.results_list.count() == 0

    def test_worker_no_results_clears_results_list(
        self, qtbot, widget: UserSearchWidget, mock_search_fn: MagicMock
    ) -> None:
        # pre-populate, then search returns empty
        _populate_results(widget, [_ALICE])
        mock_search_fn.return_value = []
        widget.search_field.setText("xyz")
        qtbot.waitUntil(lambda: not mock_search_fn.return_value or mock_search_fn.called, timeout=1500)
        # wait for the results slot to run
        qtbot.waitUntil(lambda: widget.results_list.count() == 0, timeout=1500)


# ---------------------------------------------------------------------------
# Getter and selection_changed signal
# ---------------------------------------------------------------------------


class TestGetterAndSignal:
    def test_get_selected_account_ids_returns_correct_ids(
        self, qtbot, widget: UserSearchWidget
    ) -> None:
        _populate_results(widget, [_ALICE, _BOB])
        qtbot.mouseClick(widget.btn_add_all, Qt.MouseButton.LeftButton)
        ids = widget.get_selected_account_ids()
        assert set(ids) == {"acc-alice", "acc-bob"}

    def test_get_selected_account_ids_empty_when_nothing_selected(
        self, widget: UserSearchWidget
    ) -> None:
        assert widget.get_selected_account_ids() == []

    def test_selection_changed_emitted_on_add_one(
        self, qtbot, widget: UserSearchWidget
    ) -> None:
        _populate_results(widget, [_ALICE])
        widget.results_list.setCurrentRow(0)
        with qtbot.waitSignal(widget.selection_changed, timeout=500):
            qtbot.mouseClick(widget.btn_add_one, Qt.MouseButton.LeftButton)

    def test_selection_changed_emitted_on_add_all(
        self, qtbot, widget: UserSearchWidget
    ) -> None:
        _populate_results(widget, [_ALICE])
        with qtbot.waitSignal(widget.selection_changed, timeout=500):
            qtbot.mouseClick(widget.btn_add_all, Qt.MouseButton.LeftButton)

    def test_selection_changed_emitted_on_rem_one(
        self, qtbot, widget: UserSearchWidget
    ) -> None:
        _add_to_selected(widget, _ALICE)
        widget.selected_list.setCurrentRow(0)
        with qtbot.waitSignal(widget.selection_changed, timeout=500):
            qtbot.mouseClick(widget.btn_rem_one, Qt.MouseButton.LeftButton)

    def test_selection_changed_emitted_on_rem_all(
        self, qtbot, widget: UserSearchWidget
    ) -> None:
        _add_to_selected(widget, _ALICE)
        with qtbot.waitSignal(widget.selection_changed, timeout=500):
            qtbot.mouseClick(widget.btn_rem_all, Qt.MouseButton.LeftButton)

    def test_selection_changed_emitted_on_double_click_left(
        self, qtbot, widget: UserSearchWidget
    ) -> None:
        _populate_results(widget, [_ALICE])
        item = widget.results_list.item(0)
        assert item is not None
        with qtbot.waitSignal(widget.selection_changed, timeout=500):
            widget.results_list.itemDoubleClicked.emit(item)

    def test_selection_changed_emitted_on_double_click_right(
        self, qtbot, widget: UserSearchWidget
    ) -> None:
        _add_to_selected(widget, _ALICE)
        item = widget.selected_list.item(0)
        assert item is not None
        with qtbot.waitSignal(widget.selection_changed, timeout=500):
            widget.selected_list.itemDoubleClicked.emit(item)

    def test_selection_changed_not_emitted_on_empty_add_all(
        self, qtbot, widget: UserSearchWidget
    ) -> None:
        assert widget.results_list.count() == 0
        with qtbot.assertNotEmitted(widget.selection_changed):
            qtbot.mouseClick(widget.btn_add_all, Qt.MouseButton.LeftButton)


# ---------------------------------------------------------------------------
# is_valid -- Etappe 4 retrofit
# ---------------------------------------------------------------------------


class TestIsValid:
    def test_valid_when_at_least_one_user_selected(
        self, widget: UserSearchWidget
    ) -> None:
        _add_to_selected(widget, _ALICE)
        assert widget.is_valid() is True

    def test_invalid_when_no_users_selected(self, widget: UserSearchWidget) -> None:
        assert widget.selected_list.count() == 0
        assert widget.is_valid() is False

    def test_valid_becomes_invalid_after_removing_all(
        self, qtbot, widget: UserSearchWidget
    ) -> None:
        _add_to_selected(widget, _ALICE)
        assert widget.is_valid() is True
        qtbot.mouseClick(widget.btn_rem_all, Qt.MouseButton.LeftButton)
        assert widget.is_valid() is False
