"""Tests for MainWindow -- Etappe 5b (cancel, closeEvent, result buttons)."""

from __future__ import annotations

import threading
from collections.abc import Iterator
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtCore import QSettings, Qt, QThread
from PySide6.QtGui import QCloseEvent, QDesktopServices
from PySide6.QtWidgets import QListWidgetItem

from jwe.config import ExportConfig
from jwe.exporter import ExportProgress, ExportResult
from jwe.gui.main_window import MainWindow

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _quick_export_gen(
    config: ExportConfig,
    cancel_event: threading.Event,
) -> Iterator[ExportProgress | ExportResult]:
    yield ExportProgress(issues_seen=3, worklogs_written=7)
    yield ExportResult(
        issues_seen=3,
        worklogs_written=7,
        total_time_spent_seconds=1800,
        output_path="/tmp/out.csv",
    )


def _cancelled_export_gen(
    config: ExportConfig,
    cancel_event: threading.Event,
) -> Iterator[ExportProgress | ExportResult]:
    yield ExportProgress(
        issues_seen=0, worklogs_written=0, message="Export cancelled."
    )
    # returns without ExportResult -- worker emits cancelled


def _fill_auth(mw: MainWindow) -> None:
    mw.auth_widget.sa_panel.cloud_id_field.setText("cloud-id-abc")
    mw.auth_widget.sa_panel.email_field.setText("bot@serviceaccount.atlassian.com")
    mw.auth_widget.sa_panel.token_field.setText("secret")


def _add_one_user(mw: MainWindow, account_id: str = "acc-1") -> None:
    item = QListWidgetItem("Test User")
    item.setData(Qt.ItemDataRole.UserRole, account_id)
    mw.user_search_widget.selected_list.addItem(item)
    mw.user_search_widget.selection_changed.emit()


def _make_all_valid(mw: MainWindow, tmp_path: Path) -> None:
    _fill_auth(mw)
    _add_one_user(mw)
    mw.output_widget.output_dir_field.setText(str(tmp_path))


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def isolated_settings(tmp_path: Path) -> QSettings:
    return QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)


@pytest.fixture
def mock_svc() -> MagicMock:
    svc = MagicMock()
    svc.load_token.return_value = None
    svc.run_export.side_effect = _quick_export_gen
    return svc


# ---------------------------------------------------------------------------
# T22 / T23 / T24: _on_cancel_clicked
# ---------------------------------------------------------------------------


class TestOnCancelClicked:
    def test_cancel_event_set_on_cancel_clicked(
        self, qtbot, isolated_settings: QSettings
    ) -> None:
        mw = MainWindow(_settings=isolated_settings)
        qtbot.addWidget(mw)
        cancel_event = threading.Event()
        mw._cancel_event = cancel_event
        mw.status_widget.start_progress_display()

        mw._on_cancel_clicked()

        assert cancel_event.is_set()

    def test_cancel_event_not_set_before_cancel_clicked(
        self, qtbot, isolated_settings: QSettings
    ) -> None:
        mw = MainWindow(_settings=isolated_settings)
        qtbot.addWidget(mw)
        cancel_event = threading.Event()
        mw._cancel_event = cancel_event

        assert not cancel_event.is_set()

    def test_cancel_btn_disabled_on_cancel_clicked(
        self, qtbot, isolated_settings: QSettings
    ) -> None:
        mw = MainWindow(_settings=isolated_settings)
        qtbot.addWidget(mw)
        mw._cancel_event = threading.Event()
        mw.status_widget.start_progress_display()

        mw._on_cancel_clicked()

        assert not mw.status_widget.cancel_btn.isEnabled()


# ---------------------------------------------------------------------------
# T25 / T26 / T27 / T28 / T29: closeEvent
# ---------------------------------------------------------------------------


class TestCloseEvent:
    def test_close_event_accepted_without_export(
        self, qtbot, isolated_settings: QSettings
    ) -> None:
        mw = MainWindow(_settings=isolated_settings)
        qtbot.addWidget(mw)
        # No export thread at all.
        event = QCloseEvent()
        mw.closeEvent(event)
        assert event.isAccepted()

    def test_close_event_shows_dialog_during_export(
        self, qtbot, isolated_settings: QSettings
    ) -> None:
        mw = MainWindow(_settings=isolated_settings)
        qtbot.addWidget(mw)
        mock_thread = MagicMock(spec=QThread)
        mock_thread.isRunning.return_value = True
        mock_thread.wait.return_value = True
        mw._export_thread = mock_thread
        mw._cancel_event = threading.Event()

        dialog_called: list[bool] = []
        mw._confirm_close_during_export = lambda: (  # type: ignore[method-assign]
            dialog_called.append(True) or True
        )

        event = QCloseEvent()
        mw.closeEvent(event)

        assert dialog_called

    def test_close_event_ignored_when_dialog_rejected(
        self, qtbot, isolated_settings: QSettings
    ) -> None:
        mw = MainWindow(_settings=isolated_settings)
        qtbot.addWidget(mw)
        mock_thread = MagicMock(spec=QThread)
        mock_thread.isRunning.return_value = True
        mw._export_thread = mock_thread
        mw._cancel_event = threading.Event()

        mw._confirm_close_during_export = lambda: False  # type: ignore[method-assign]

        event = QCloseEvent()
        mw.closeEvent(event)

        assert not event.isAccepted()
        mock_thread.quit.assert_not_called()

    def test_close_event_accepted_when_dialog_confirmed(
        self, qtbot, isolated_settings: QSettings
    ) -> None:
        mw = MainWindow(_settings=isolated_settings)
        qtbot.addWidget(mw)
        mock_thread = MagicMock(spec=QThread)
        mock_thread.isRunning.return_value = True
        mock_thread.wait.return_value = True
        mw._export_thread = mock_thread
        mw._cancel_event = threading.Event()

        mw._confirm_close_during_export = lambda: True  # type: ignore[method-assign]

        event = QCloseEvent()
        mw.closeEvent(event)

        mock_thread.quit.assert_called_once()
        mock_thread.wait.assert_called_once_with(2000)
        assert event.isAccepted()

    def test_close_event_not_ignored_without_running_export(
        self, qtbot, isolated_settings: QSettings
    ) -> None:
        mw = MainWindow(_settings=isolated_settings)
        qtbot.addWidget(mw)
        mock_thread = MagicMock(spec=QThread)
        mock_thread.isRunning.return_value = False
        mw._export_thread = mock_thread

        event = QCloseEvent()
        mw.closeEvent(event)

        assert event.isAccepted()


# ---------------------------------------------------------------------------
# T30 / T31 / T32: open URL handlers
# ---------------------------------------------------------------------------


class TestOpenUrlHandlers:
    def test_open_csv_calls_open_url(
        self, qtbot, isolated_settings: QSettings
    ) -> None:
        mw = MainWindow(_settings=isolated_settings)
        qtbot.addWidget(mw)
        mw._last_output_path = "/tmp/out.csv"

        calls: list[str] = []
        with patch.object(QDesktopServices, "openUrl", lambda url: calls.append(url.toLocalFile())):
            mw._on_open_csv_clicked()

        assert len(calls) == 1
        assert "out.csv" in calls[0]

    def test_open_folder_calls_open_url(
        self, qtbot, isolated_settings: QSettings
    ) -> None:
        mw = MainWindow(_settings=isolated_settings)
        qtbot.addWidget(mw)
        mw._last_output_path = "/tmp/out.csv"

        calls: list[str] = []
        with patch.object(QDesktopServices, "openUrl", lambda url: calls.append(url.toLocalFile())):
            mw._on_open_folder_clicked()

        assert len(calls) == 1
        # The folder URL must point to the parent directory, not the file itself.
        assert "out.csv" not in calls[0]

    def test_open_csv_not_called_without_output_path(
        self, qtbot, isolated_settings: QSettings
    ) -> None:
        mw = MainWindow(_settings=isolated_settings)
        qtbot.addWidget(mw)
        # _last_output_path is None by default.

        calls: list[str] = []
        with patch.object(QDesktopServices, "openUrl", lambda url: calls.append(url.toLocalFile())):
            mw._on_open_csv_clicked()

        assert calls == []


# ---------------------------------------------------------------------------
# T33 / T34: result buttons visibility after export
# ---------------------------------------------------------------------------


class TestResultButtonsVisibility:
    def test_result_buttons_visible_after_export_finished(
        self,
        qtbot,
        isolated_settings: QSettings,
        mock_svc: MagicMock,
        tmp_path: Path,
    ) -> None:
        mw = MainWindow(_settings=isolated_settings, service=mock_svc)
        qtbot.addWidget(mw)
        mw.show()
        _make_all_valid(mw, tmp_path)

        qtbot.mouseClick(mw.status_widget.export_btn, Qt.MouseButton.LeftButton)
        qtbot.waitUntil(
            lambda: mw.status_widget.export_btn.isEnabled(), timeout=3000
        )

        assert mw.status_widget._result_row.isVisible()

    def test_result_buttons_not_visible_after_export_cancelled(
        self,
        qtbot,
        isolated_settings: QSettings,
        tmp_path: Path,
    ) -> None:
        mock_svc = MagicMock()
        mock_svc.load_token.return_value = None
        mock_svc.run_export.side_effect = _cancelled_export_gen

        mw = MainWindow(_settings=isolated_settings, service=mock_svc)
        qtbot.addWidget(mw)
        mw.show()
        _make_all_valid(mw, tmp_path)

        qtbot.mouseClick(mw.status_widget.export_btn, Qt.MouseButton.LeftButton)
        qtbot.waitUntil(
            lambda: mw.status_widget.export_btn.isEnabled(), timeout=3000
        )

        assert not mw.status_widget._result_row.isVisible()
