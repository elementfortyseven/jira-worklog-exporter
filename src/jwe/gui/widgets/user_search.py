"""User search and selection shuttle widget (Etappe 3)."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from PySide6.QtCore import QSize, Qt, QThread, QTimer, Signal
from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from jwe.api.user import User
from jwe.gui.workers.user_search import UserSearchWorker

logger = logging.getLogger(__name__)


class UserSearchWidget(QGroupBox):
    """Search for Jira users and build the selected-users list."""

    selection_changed = Signal()

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        search_fn: Callable[[str], list[User]] | None = None,
    ) -> None:
        super().__init__("Users", parent)  # i18n: section.user_search.title
        self._search_fn = search_fn
        self._search_thread: QThread | None = None
        self._search_worker: UserSearchWorker | None = None
        self._debounce_timer = QTimer(self)
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.setInterval(400)
        self._build_ui()
        self._debounce_timer.timeout.connect(self._on_debounce_fired)

    def set_search_fn(self, fn: Callable[[str], list[User]]) -> None:
        """Bind the search function (called from MainWindow once auth config is ready)."""
        self._search_fn = fn

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(8, 16, 8, 8)
        outer.setSpacing(6)

        # Search field
        self.search_field = QLineEdit()
        self.search_field.setPlaceholderText("Search users...")  # i18n: user_search.search.placeholder
        outer.addWidget(self.search_field)

        # Status label sits directly under the search field
        self.search_status_label = QLabel("")
        outer.addWidget(self.search_status_label)

        # Shuttle row: left list | button column | right list
        shuttle_row = QWidget()
        shuttle_layout = QHBoxLayout(shuttle_row)
        shuttle_layout.setContentsMargins(0, 0, 0, 0)
        shuttle_layout.setSpacing(6)

        self.results_list = QListWidget()
        self.results_list.setMinimumHeight(150)
        self.results_list.setMinimumWidth(200)
        self.results_list.setSpacing(2)
        shuttle_layout.addWidget(self.results_list)

        btn_widget = QWidget()
        btn_layout = QVBoxLayout(btn_widget)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        self.btn_add_one = QPushButton(">")   # i18n: user_search.btn.add_one
        self.btn_add_all = QPushButton(">>")  # i18n: user_search.btn.add_all
        self.btn_rem_one = QPushButton("<")   # i18n: user_search.btn.rem_one
        self.btn_rem_all = QPushButton("<<")  # i18n: user_search.btn.rem_all
        for btn in (self.btn_add_one, self.btn_add_all, self.btn_rem_one, self.btn_rem_all):
            btn.setFixedWidth(40)
            btn_layout.addWidget(btn)
        shuttle_layout.addWidget(btn_widget)

        self.selected_list = QListWidget()
        self.selected_list.setMinimumHeight(150)
        self.selected_list.setMinimumWidth(200)
        self.selected_list.setSpacing(2)
        shuttle_layout.addWidget(self.selected_list)

        outer.addWidget(shuttle_row)

        self.search_field.textChanged.connect(self._on_search_text_changed)
        self.btn_add_one.clicked.connect(self._move_add_one)
        self.btn_add_all.clicked.connect(self._move_add_all)
        self.btn_rem_one.clicked.connect(self._move_rem_one)
        self.btn_rem_all.clicked.connect(self._move_rem_all)
        self.results_list.itemDoubleClicked.connect(self._on_result_double_clicked)
        self.selected_list.itemDoubleClicked.connect(self._on_selected_double_clicked)

    # ------------------------------------------------------------------
    # Debounce / search
    # ------------------------------------------------------------------

    def _on_search_text_changed(self, text: str) -> None:
        if not text.strip():
            self._debounce_timer.stop()
            self.results_list.clear()
            self.search_status_label.clear()
            return
        self._debounce_timer.start(400)

    def _on_debounce_fired(self) -> None:
        query = self.search_field.text().strip()
        if not query:
            return
        if self._search_fn is None:
            self.search_status_label.setText(
                "Authentication required"  # i18n: user_search.status.auth_required
            )
            return
        self.search_status_label.setText("Searching...")  # i18n: user_search.status.searching
        worker = UserSearchWorker(query, self._search_fn)
        thread = QThread()
        worker.moveToThread(thread)
        worker.results.connect(self._on_search_results)
        worker.failed.connect(self._on_search_failed)
        worker.results.connect(lambda _: thread.quit())
        worker.failed.connect(lambda _: thread.quit())
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._clear_search_refs)
        thread.started.connect(worker.run)
        self._search_thread = thread
        self._search_worker = worker
        thread.start()

    def _on_search_results(self, users: list[Any]) -> None:
        self.search_status_label.clear()
        self.results_list.clear()
        for user in users:
            item = QListWidgetItem(f"{user.display_name}\n{user.email}")
            item.setData(Qt.ItemDataRole.UserRole, user.account_id)
            item.setSizeHint(QSize(-1, 44))
            self.results_list.addItem(item)

    def _on_search_failed(self, message: str) -> None:
        self.results_list.clear()
        self.search_status_label.setText(message)

    def _clear_search_refs(self) -> None:
        self._search_thread = None
        self._search_worker = None

    # ------------------------------------------------------------------
    # Shuttle helpers
    # ------------------------------------------------------------------

    def _ids_in_selected(self) -> set[str]:
        return {
            self.selected_list.item(i).data(Qt.ItemDataRole.UserRole)
            for i in range(self.selected_list.count())
        }

    @staticmethod
    def _copy_item(source: QListWidgetItem) -> QListWidgetItem:
        new = QListWidgetItem(source.text())
        new.setData(Qt.ItemDataRole.UserRole, source.data(Qt.ItemDataRole.UserRole))
        new.setSizeHint(QSize(-1, 44))
        return new

    def _move_add_one(self) -> None:
        selected = self.results_list.selectedItems()
        if not selected:
            return
        existing = self._ids_in_selected()
        rows = sorted(
            [self.results_list.row(item) for item in selected], reverse=True
        )
        changed = False
        for row in rows:
            item = self.results_list.item(row)
            if item is None:
                continue
            account_id: str = item.data(Qt.ItemDataRole.UserRole)
            if account_id not in existing:
                self.selected_list.addItem(self._copy_item(item))
                existing.add(account_id)
                self.results_list.takeItem(row)
                changed = True
            # duplicate: leave in left list, no-op
        if changed:
            self.selection_changed.emit()

    def _move_add_all(self) -> None:
        if self.results_list.count() == 0:
            return
        existing = self._ids_in_selected()
        changed = False
        for row in range(self.results_list.count() - 1, -1, -1):
            item = self.results_list.item(row)
            if item is None:
                continue
            account_id: str = item.data(Qt.ItemDataRole.UserRole)
            if account_id not in existing:
                self.selected_list.addItem(self._copy_item(item))
                existing.add(account_id)
                changed = True
            self.results_list.takeItem(row)  # always clear from left
        if changed:
            self.selection_changed.emit()

    def _move_rem_one(self) -> None:
        selected = self.selected_list.selectedItems()
        if not selected:
            return
        rows = sorted(
            [self.selected_list.row(item) for item in selected], reverse=True
        )
        for row in rows:
            self.selected_list.takeItem(row)
        self.selection_changed.emit()

    def _move_rem_all(self) -> None:
        if self.selected_list.count() == 0:
            return
        self.selected_list.clear()
        self.selection_changed.emit()

    def _on_result_double_clicked(self, item: QListWidgetItem) -> None:
        account_id: str = item.data(Qt.ItemDataRole.UserRole)
        if account_id in self._ids_in_selected():
            return  # already selected, leave in left list
        row = self.results_list.row(item)
        self.selected_list.addItem(self._copy_item(item))
        self.results_list.takeItem(row)
        self.selection_changed.emit()

    def _on_selected_double_clicked(self, item: QListWidgetItem) -> None:
        row = self.selected_list.row(item)
        self.selected_list.takeItem(row)
        self.selection_changed.emit()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_selected_account_ids(self) -> list[str]:
        """Return account IDs of all users in the selected list."""
        return [
            self.selected_list.item(i).data(Qt.ItemDataRole.UserRole)
            for i in range(self.selected_list.count())
        ]

    # ------------------------------------------------------------------
    # Thread lifecycle (called from MainWindow.closeEvent)
    # ------------------------------------------------------------------

    def stop_running_threads(self) -> None:
        """Abort any in-flight search worker."""
        if self._search_thread is not None and self._search_thread.isRunning():
            self._search_thread.quit()

    # ------------------------------------------------------------------
    # i18n
    # ------------------------------------------------------------------

    def retranslate_ui(self, lang: str) -> None:
        """Update translatable strings for *lang*."""
