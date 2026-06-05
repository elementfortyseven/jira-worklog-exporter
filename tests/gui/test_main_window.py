"""Tests for MainWindow -- Etappen 1, 4, and connection-verify wiring."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from PySide6.QtCore import QByteArray, QDate, QSettings, Qt
from PySide6.QtWidgets import QListWidgetItem

from jwe.api.user import User
from jwe.config import ExportConfig
from jwe.gui.main_window import MainWindow

_FAKE_USER = User(account_id="acc-1", display_name="Test", email="t@t.com", active=True)


class TestMainWindowInstantiates:
    """MainWindow can be created without error."""

    def test_has_all_five_section_widgets(self, main_window: MainWindow) -> None:
        assert hasattr(main_window, "auth_widget")
        assert hasattr(main_window, "user_search_widget")
        assert hasattr(main_window, "filter_widget")
        assert hasattr(main_window, "output_widget")
        assert hasattr(main_window, "status_widget")

    def test_initial_lang_defaults_to_de(self, main_window: MainWindow) -> None:
        assert main_window._lang == "de"

    def test_initial_lang_override(self, qtbot, isolated_settings: QSettings) -> None:
        w = MainWindow(initial_lang="en", _settings=isolated_settings)
        qtbot.addWidget(w)
        assert w._lang == "en"


class TestLanguageToggle:
    """Toggle button flips _lang and calls retranslate_ui on all section widgets."""

    def test_flips_lang_de_to_en(self, qtbot, main_window: MainWindow) -> None:
        assert main_window._lang == "de"
        qtbot.mouseClick(main_window.lang_btn, Qt.MouseButton.LeftButton)
        assert main_window._lang == "en"

    def test_flips_lang_en_to_de(self, qtbot, isolated_settings: QSettings) -> None:
        w = MainWindow(initial_lang="en", _settings=isolated_settings)
        qtbot.addWidget(w)
        qtbot.mouseClick(w.lang_btn, Qt.MouseButton.LeftButton)
        assert w._lang == "de"

    def test_calls_retranslate_ui_on_all_five_widgets(
        self, qtbot, main_window: MainWindow
    ) -> None:
        with (
            patch.object(main_window.auth_widget, "retranslate_ui") as m_auth,
            patch.object(main_window.user_search_widget, "retranslate_ui") as m_user,
            patch.object(main_window.filter_widget, "retranslate_ui") as m_filter,
            patch.object(main_window.output_widget, "retranslate_ui") as m_output,
            patch.object(main_window.status_widget, "retranslate_ui") as m_status,
        ):
            qtbot.mouseClick(main_window.lang_btn, Qt.MouseButton.LeftButton)

        m_auth.assert_called_once_with("en")
        m_user.assert_called_once_with("en")
        m_filter.assert_called_once_with("en")
        m_output.assert_called_once_with("en")
        m_status.assert_called_once_with("en")

    def test_language_changed_signal_emitted(
        self, qtbot, main_window: MainWindow
    ) -> None:
        received: list[str] = []
        main_window.language_changed.connect(received.append)
        qtbot.mouseClick(main_window.lang_btn, Qt.MouseButton.LeftButton)
        assert received == ["en"]


class TestQSettingsGeometryRoundtrip:
    """closeEvent saves geometry; next MainWindow with same settings restores it."""

    def test_saves_and_restores_geometry(self, qtbot, tmp_path: Path) -> None:
        settings_file = str(tmp_path / "geo_test.ini")

        s1 = QSettings(settings_file, QSettings.Format.IniFormat)
        w1 = MainWindow(_settings=s1)
        qtbot.addWidget(w1)
        w1.show()
        qtbot.waitExposed(w1)
        w1.resize(1100, 750)
        original_geo: QByteArray = w1.saveGeometry()
        w1.close()
        s1.sync()

        s2 = QSettings(settings_file, QSettings.Format.IniFormat)
        w2 = MainWindow(_settings=s2)
        qtbot.addWidget(w2)

        saved_raw = s2.value("geometry", QByteArray())
        assert isinstance(saved_raw, QByteArray), "geometry must be a QByteArray"
        assert not saved_raw.isEmpty(), "geometry must not be empty after save"
        assert saved_raw == original_geo, "restored geometry must match saved geometry"


# ---------------------------------------------------------------------------
# Export button integration -- Etappe 4
# ---------------------------------------------------------------------------


def _fill_auth(mw: MainWindow) -> None:
    """Fill SA auth fields so auth_widget.is_valid() returns True."""
    mw.auth_widget.sa_panel.cloud_id_field.setText("cloud-id-abc")
    mw.auth_widget.sa_panel.email_field.setText("bot@sa.atlassian.com")
    mw.auth_widget.sa_panel.token_field.setText("secret")


def _add_one_user(mw: MainWindow) -> None:
    """Add a user to the selected list so user_search_widget.is_valid() returns True."""
    item = QListWidgetItem("Test User")
    item.setData(Qt.ItemDataRole.UserRole, "acc-1")
    mw.user_search_widget.selected_list.addItem(item)
    mw.user_search_widget.selection_changed.emit()


def _make_all_valid(mw: MainWindow, tmp_path: Path) -> None:
    _fill_auth(mw)
    _add_one_user(mw)
    mw.output_widget.output_dir_field.setText(str(tmp_path))
    # filter defaults are valid (current month, no project keys)


class TestExportButtonIntegration:
    def test_export_btn_disabled_when_auth_invalid(
        self, main_window: MainWindow, tmp_path: Path
    ) -> None:
        _add_one_user(main_window)
        main_window.output_widget.output_dir_field.setText(str(tmp_path))
        # auth fields are empty by default
        assert not main_window.status_widget.export_btn.isEnabled()

    def test_export_btn_disabled_when_no_users_selected(
        self, main_window: MainWindow, tmp_path: Path
    ) -> None:
        _fill_auth(main_window)
        main_window.output_widget.output_dir_field.setText(str(tmp_path))
        # no users added
        assert not main_window.status_widget.export_btn.isEnabled()

    def test_export_btn_disabled_when_filter_invalid(
        self, main_window: MainWindow, tmp_path: Path
    ) -> None:
        _make_all_valid(main_window, tmp_path)
        # invert date range
        main_window.filter_widget.from_date.setDate(QDate(2026, 2, 1))
        main_window.filter_widget.to_date.setDate(QDate(2026, 1, 1))
        assert not main_window.status_widget.export_btn.isEnabled()

    def test_export_btn_disabled_when_output_invalid(
        self, main_window: MainWindow, tmp_path: Path
    ) -> None:
        _make_all_valid(main_window, tmp_path)
        main_window.output_widget.output_dir_field.setText("")
        assert not main_window.status_widget.export_btn.isEnabled()

    def test_export_btn_enabled_when_all_valid(
        self, main_window: MainWindow, tmp_path: Path
    ) -> None:
        _make_all_valid(main_window, tmp_path)
        assert main_window.status_widget.export_btn.isEnabled()


class TestQSettingsNewFields:
    def test_saves_and_restores_filter_project_keys(
        self, qtbot, tmp_path: Path
    ) -> None:
        settings_file = str(tmp_path / "s.ini")
        s1 = QSettings(settings_file, QSettings.Format.IniFormat)
        w1 = MainWindow(_settings=s1)
        qtbot.addWidget(w1)
        w1.filter_widget.project_keys_field.setText("PROJ")
        w1.close()
        s1.sync()

        s2 = QSettings(settings_file, QSettings.Format.IniFormat)
        w2 = MainWindow(_settings=s2)
        qtbot.addWidget(w2)
        assert w2.filter_widget.project_keys_field.text() == "PROJ"

    def test_saves_and_restores_output_dir(
        self, qtbot, tmp_path: Path
    ) -> None:
        settings_file = str(tmp_path / "s.ini")
        target_dir = str(tmp_path)
        s1 = QSettings(settings_file, QSettings.Format.IniFormat)
        w1 = MainWindow(_settings=s1)
        qtbot.addWidget(w1)
        w1.output_widget.output_dir_field.setText(target_dir)
        w1.close()
        s1.sync()

        s2 = QSettings(settings_file, QSettings.Format.IniFormat)
        w2 = MainWindow(_settings=s2)
        qtbot.addWidget(w2)
        assert w2.output_widget.output_dir_field.text() == target_dir


# ---------------------------------------------------------------------------
# closeEvent teardown contract (JWE-31)
# ---------------------------------------------------------------------------


class TestCloseEventTeardown:
    """closeEvent must quit and join the export thread before returning."""

    def test_export_thread_stopped_after_close(
        self, qtbot, isolated_settings: QSettings
    ) -> None:
        mock_svc = MagicMock()
        mock_svc.load_token.return_value = None
        w = MainWindow(_settings=isolated_settings, service=mock_svc)
        qtbot.addWidget(w)

        # Start the thread directly -- same path _on_export_clicked takes on
        # first export.  Thread idles in its event loop; no slot is invoked.
        w._export_thread.start()
        assert w._export_thread.isRunning(), "thread must be running before close"

        w.close()  # triggers closeEvent -> quit() + wait(2000)

        assert not w._export_thread.isRunning(), (
            "closeEvent must stop _export_thread before returning"
        )


# ---------------------------------------------------------------------------
# Connection-verify wiring (bugfix: UserSearchWidget search_fn)
# ---------------------------------------------------------------------------

_SA_CONFIG = ExportConfig(
    cloud_id="aaaabbbb-cccc-dddd-eeee-ffffffffffff",
    service_account_email="bot@serviceaccount.atlassian.com",
    api_token="token",
)


class TestConnectionVerifiedWiring:
    # MW-4: before any connection_verified, _search_fn on the worker is None
    def test_search_fn_is_none_before_connection_verified(
        self, main_window: MainWindow
    ) -> None:
        assert main_window.user_search_widget._search_worker._search_fn is None

    # MW-1: after connection_verified signal, _search_fn is set on the worker
    def test_search_fn_set_after_connection_verified(
        self, main_window: MainWindow
    ) -> None:
        main_window.auth_widget.connection_verified.emit(_SA_CONFIG)
        assert main_window.user_search_widget._search_worker._search_fn is not None

    # MW-2: after connection_invalidated, _search_fn on the worker is None again
    def test_search_fn_cleared_after_connection_invalidated(
        self, main_window: MainWindow
    ) -> None:
        main_window.auth_widget.connection_verified.emit(_SA_CONFIG)
        main_window.auth_widget.connection_invalidated.emit()
        assert main_window.user_search_widget._search_worker._search_fn is None

    # MW-3: search_fn closure calls service.search_users with the correct config
    def test_search_fn_closure_calls_search_users_with_correct_config(
        self, qtbot, isolated_settings: QSettings
    ) -> None:
        mock_svc = MagicMock()
        mock_svc.load_token.return_value = None
        mock_svc.search_users.return_value = []
        mw = MainWindow(_settings=isolated_settings, service=mock_svc)
        qtbot.addWidget(mw)

        mw.auth_widget.connection_verified.emit(_SA_CONFIG)
        fn = mw.user_search_widget._search_worker._search_fn
        assert fn is not None
        fn("alice")

        mock_svc.search_users.assert_called_once_with(_SA_CONFIG, "alice")
