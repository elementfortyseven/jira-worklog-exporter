"""Tests for MainWindow export wiring -- Etappe 5a."""

from __future__ import annotations

import threading
from collections.abc import Iterator
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from PySide6.QtCore import QDate, QSettings, Qt
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


def _failing_export_gen(
    config: ExportConfig,
    cancel_event: threading.Event,
) -> Iterator[ExportProgress | ExportResult]:
    raise RuntimeError("network timeout")
    yield  # make it a generator


@pytest.fixture
def isolated_settings(tmp_path: Path) -> QSettings:
    return QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)


@pytest.fixture
def mock_svc() -> MagicMock:
    svc = MagicMock()
    svc.load_token.return_value = None
    svc.run_export.side_effect = _quick_export_gen
    return svc


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
# M-1: export button click starts the worker (run_export called)
# ---------------------------------------------------------------------------


class TestExportWorkerStarted:
    def test_run_export_called_on_btn_click(
        self, qtbot, make_main_window, mock_svc: MagicMock, tmp_path: Path
    ) -> None:
        mw = make_main_window(service=mock_svc)
        _make_all_valid(mw, tmp_path)

        qtbot.mouseClick(mw.status_widget.export_btn, Qt.MouseButton.LeftButton)
        qtbot.waitUntil(
            lambda: mw.status_widget.export_btn.isEnabled(), timeout=3000
        )

        mock_svc.run_export.assert_called_once()

    def test_run_export_not_called_before_click(
        self, qtbot, isolated_settings: QSettings, mock_svc: MagicMock, tmp_path: Path
    ) -> None:
        mw = MainWindow(_settings=isolated_settings, service=mock_svc)
        qtbot.addWidget(mw)
        _make_all_valid(mw, tmp_path)

        mock_svc.run_export.assert_not_called()


# ---------------------------------------------------------------------------
# M-2: export button disabled while running
# ---------------------------------------------------------------------------


class TestExportBtnDisabledDuringExport:
    def test_export_btn_disabled_while_running(
        self, qtbot, make_main_window, tmp_path: Path
    ) -> None:
        started = threading.Event()
        unblock = threading.Event()

        def slow_gen(
            config: ExportConfig, cancel: threading.Event
        ) -> Iterator[ExportProgress | ExportResult]:
            started.set()
            unblock.wait(timeout=5.0)
            yield ExportResult(
                issues_seen=0,
                worklogs_written=0,
                total_time_spent_seconds=0,
                output_path=None,
            )

        mock_svc = MagicMock()
        mock_svc.load_token.return_value = None
        mock_svc.run_export.side_effect = slow_gen
        mw = make_main_window(service=mock_svc)
        _make_all_valid(mw, tmp_path)

        qtbot.mouseClick(mw.status_widget.export_btn, Qt.MouseButton.LeftButton)
        qtbot.waitUntil(lambda: started.is_set(), timeout=3000)

        assert not mw.status_widget.export_btn.isEnabled()

        unblock.set()
        qtbot.waitUntil(
            lambda: mw.status_widget.export_btn.isEnabled(), timeout=3000
        )


# ---------------------------------------------------------------------------
# M-3: export button re-enabled after finished
# ---------------------------------------------------------------------------


class TestExportBtnReenabledAfterFinished:
    def test_btn_re_enabled_after_successful_export(
        self, qtbot, make_main_window, mock_svc: MagicMock, tmp_path: Path
    ) -> None:
        mw = make_main_window(service=mock_svc)
        _make_all_valid(mw, tmp_path)

        qtbot.mouseClick(mw.status_widget.export_btn, Qt.MouseButton.LeftButton)
        qtbot.waitUntil(
            lambda: mw.status_widget.export_btn.isEnabled(), timeout=3000
        )

        assert mw.status_widget.export_btn.isEnabled()

    def test_progress_bar_stopped_after_finished(
        self, qtbot, make_main_window, mock_svc: MagicMock, tmp_path: Path
    ) -> None:
        mw = make_main_window(service=mock_svc)
        mw.show()
        qtbot.waitExposed(mw)
        _make_all_valid(mw, tmp_path)

        qtbot.mouseClick(mw.status_widget.export_btn, Qt.MouseButton.LeftButton)
        qtbot.waitUntil(
            lambda: mw.status_widget.export_btn.isEnabled(), timeout=3000
        )

        assert mw.status_widget.progress_bar.maximum() != 0


# ---------------------------------------------------------------------------
# M-4: export button re-enabled after failed
# ---------------------------------------------------------------------------


class TestExportBtnReenabledAfterFailed:
    def test_btn_re_enabled_after_failed_export(
        self, qtbot, make_main_window, tmp_path: Path
    ) -> None:
        mock_svc = MagicMock()
        mock_svc.load_token.return_value = None
        mock_svc.run_export.side_effect = _failing_export_gen
        mw = make_main_window(service=mock_svc)
        _make_all_valid(mw, tmp_path)

        qtbot.mouseClick(mw.status_widget.export_btn, Qt.MouseButton.LeftButton)
        qtbot.waitUntil(
            lambda: mw.status_widget.export_btn.isEnabled(), timeout=3000
        )

        assert mw.status_widget.export_btn.isEnabled()

    def test_log_panel_shows_error_after_failed(
        self, qtbot, make_main_window, tmp_path: Path
    ) -> None:
        mock_svc = MagicMock()
        mock_svc.load_token.return_value = None
        mock_svc.run_export.side_effect = _failing_export_gen
        mw = make_main_window(service=mock_svc)
        _make_all_valid(mw, tmp_path)

        qtbot.mouseClick(mw.status_widget.export_btn, Qt.MouseButton.LeftButton)
        qtbot.waitUntil(
            lambda: mw.status_widget.export_btn.isEnabled(), timeout=3000
        )

        assert "network timeout" in mw.status_widget.log_panel.toPlainText()


# ---------------------------------------------------------------------------
# M-5: _build_config collects account_ids
# ---------------------------------------------------------------------------


class TestBuildConfigAccountIds:
    def test_collects_single_account_id(
        self, qtbot, isolated_settings: QSettings, tmp_path: Path
    ) -> None:
        mw = MainWindow(_settings=isolated_settings)
        qtbot.addWidget(mw)
        _fill_auth(mw)
        _add_one_user(mw, account_id="acc-xyz")
        mw.output_widget.output_dir_field.setText(str(tmp_path))

        config = mw._build_config()

        assert "acc-xyz" in config.user_account_ids

    def test_collects_multiple_account_ids(
        self, qtbot, isolated_settings: QSettings, tmp_path: Path
    ) -> None:
        mw = MainWindow(_settings=isolated_settings)
        qtbot.addWidget(mw)
        _fill_auth(mw)
        _add_one_user(mw, account_id="acc-1")
        _add_one_user(mw, account_id="acc-2")
        mw.output_widget.output_dir_field.setText(str(tmp_path))

        config = mw._build_config()

        assert set(config.user_account_ids) == {"acc-1", "acc-2"}

    def test_empty_account_ids_when_no_users_selected(
        self, qtbot, isolated_settings: QSettings, tmp_path: Path
    ) -> None:
        mw = MainWindow(_settings=isolated_settings)
        qtbot.addWidget(mw)
        mw.output_widget.output_dir_field.setText(str(tmp_path))

        config = mw._build_config()

        assert config.user_account_ids == []


# ---------------------------------------------------------------------------
# M-6: _build_config collects from_date / to_date
# ---------------------------------------------------------------------------


class TestBuildConfigDates:
    def test_collects_from_date(
        self, qtbot, isolated_settings: QSettings
    ) -> None:
        mw = MainWindow(_settings=isolated_settings)
        qtbot.addWidget(mw)
        mw.filter_widget.from_date.setDate(QDate(2025, 1, 15))

        config = mw._build_config()

        assert config.from_date == date(2025, 1, 15)

    def test_collects_to_date(
        self, qtbot, isolated_settings: QSettings
    ) -> None:
        mw = MainWindow(_settings=isolated_settings)
        qtbot.addWidget(mw)
        mw.filter_widget.to_date.setDate(QDate(2025, 3, 20))

        config = mw._build_config()

        assert config.to_date == date(2025, 3, 20)


# ---------------------------------------------------------------------------
# M-7: cancel_event is passed to run_fn
# ---------------------------------------------------------------------------


class TestCancelEventPassedToRunFn:
    def test_cancel_event_is_threading_event(
        self, qtbot, make_main_window, tmp_path: Path
    ) -> None:
        received: list[threading.Event] = []

        def capturing_gen(
            config: ExportConfig, cancel: threading.Event
        ) -> Iterator[ExportProgress | ExportResult]:
            received.append(cancel)
            yield ExportResult(
                issues_seen=0,
                worklogs_written=0,
                total_time_spent_seconds=0,
                output_path=None,
            )

        mock_svc = MagicMock()
        mock_svc.load_token.return_value = None
        mock_svc.run_export.side_effect = capturing_gen
        mw = make_main_window(service=mock_svc)
        _make_all_valid(mw, tmp_path)

        qtbot.mouseClick(mw.status_widget.export_btn, Qt.MouseButton.LeftButton)
        qtbot.waitUntil(lambda: len(received) > 0, timeout=3000)

        assert isinstance(received[0], threading.Event)

    def test_cancel_event_not_set_at_start(
        self, qtbot, make_main_window, tmp_path: Path
    ) -> None:
        received: list[threading.Event] = []

        def capturing_gen(
            config: ExportConfig, cancel: threading.Event
        ) -> Iterator[ExportProgress | ExportResult]:
            received.append(cancel)
            yield ExportResult(
                issues_seen=0,
                worklogs_written=0,
                total_time_spent_seconds=0,
                output_path=None,
            )

        mock_svc = MagicMock()
        mock_svc.load_token.return_value = None
        mock_svc.run_export.side_effect = capturing_gen
        mw = make_main_window(service=mock_svc)
        _make_all_valid(mw, tmp_path)

        qtbot.mouseClick(mw.status_widget.export_btn, Qt.MouseButton.LeftButton)
        qtbot.waitUntil(lambda: len(received) > 0, timeout=3000)

        assert not received[0].is_set()
