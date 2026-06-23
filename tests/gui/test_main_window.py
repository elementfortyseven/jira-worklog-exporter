"""Tests for MainWindow -- Stages 1, 4, connection-verify wiring, JWE-34 shell, JWE-50 native chrome."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtCore import QByteArray, QDate, QPoint, QRect, QSettings, QSize, Qt
from PySide6.QtWidgets import QListWidgetItem

from jwe.api.user import User
from jwe.config import ExportConfig
from jwe.gui.main_window import (
    _HTBOTTOM,
    _HTBOTTOMLEFT,
    _HTBOTTOMRIGHT,
    _HTCAPTION,
    _HTCLIENT,
    _HTLEFT,
    _HTRIGHT,
    _HTTOP,
    _HTTOPLEFT,
    _HTTOPRIGHT,
    MainWindow,
)

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


# ---------------------------------------------------------------------------
# JWE-34: Frameless shell
# ---------------------------------------------------------------------------


class TestFramelessShell:
    """Frameless window flags and structural assertions."""

    @pytest.mark.skipif(
        sys.platform == "win32", reason="Native DWM model on Windows: no FramelessWindowHint"
    )
    def test_frameless_hint_set(self, main_window: MainWindow) -> None:
        assert main_window.windowFlags() & Qt.WindowType.FramelessWindowHint

    @pytest.mark.skipif(
        sys.platform == "win32", reason="Native DWM model on Windows: no WA_TranslucentBackground"
    )
    def test_translucent_background_set(self, main_window: MainWindow) -> None:
        assert main_window.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def test_window_frame_widget_present(self, main_window: MainWindow) -> None:
        assert hasattr(main_window, "_window_frame")
        assert main_window._window_frame.objectName() == "windowFrame"

    def test_minimum_size_800x600(self, main_window: MainWindow) -> None:
        assert main_window.minimumSize() == QSize(800, 600)

    def test_title_bar_present(self, main_window: MainWindow) -> None:
        assert hasattr(main_window, "title_bar")

    def test_title_bar_has_brand_label(self, main_window: MainWindow) -> None:
        assert main_window.title_bar.brand_label is not None

    def test_title_bar_has_de_btn(self, main_window: MainWindow) -> None:
        assert main_window.title_bar.de_btn is not None

    def test_title_bar_has_en_btn(self, main_window: MainWindow) -> None:
        assert main_window.title_bar.en_btn is not None

    def test_title_bar_has_win_min_btn(self, main_window: MainWindow) -> None:
        assert main_window.title_bar.win_min_btn is not None

    def test_title_bar_has_win_max_btn(self, main_window: MainWindow) -> None:
        assert main_window.title_bar.win_max_btn is not None

    def test_title_bar_has_win_close_btn(self, main_window: MainWindow) -> None:
        assert main_window.title_bar.win_close_btn is not None

    def test_win_min_btn_emits_minimize_requested(self, qtbot, main_window: MainWindow) -> None:
        with qtbot.waitSignal(main_window.title_bar.minimize_requested, timeout=1000):
            main_window.title_bar.win_min_btn.click()

    def test_win_max_toggles_maximized_state(self, main_window: MainWindow) -> None:
        assert not main_window._maximized
        main_window._toggle_max_restore()
        assert main_window._maximized
        main_window._toggle_max_restore()
        assert not main_window._maximized

    def test_win_close_btn_emits_close_requested(self, main_window: MainWindow) -> None:
        received: list[bool] = []
        # Disconnect from close() so the fixture window is not closed mid-test.
        main_window.title_bar.close_requested.disconnect(main_window.close)
        main_window.title_bar.close_requested.connect(lambda: received.append(True))
        main_window.title_bar.win_close_btn.click()
        assert received == [True]

    @pytest.mark.skipif(
        sys.platform == "win32", reason="Native DWM model on Windows: no pre_max_geometry"
    )
    def test_maximize_saves_pre_max_geometry(self, main_window: MainWindow) -> None:
        assert main_window._pre_max_geometry is None
        main_window._toggle_max_restore()
        assert main_window._pre_max_geometry is not None

    @pytest.mark.skipif(
        sys.platform == "win32", reason="Native DWM model on Windows: no Qt drop shadow"
    )
    def test_maximize_disables_shadow_effect(self, main_window: MainWindow) -> None:
        assert main_window._shadow_effect is not None
        main_window._toggle_max_restore()
        assert not main_window._shadow_effect.isEnabled()

    @pytest.mark.skipif(
        sys.platform == "win32", reason="Native DWM model on Windows: no Qt drop shadow"
    )
    def test_restore_re_enables_shadow_effect(self, main_window: MainWindow) -> None:
        main_window._toggle_max_restore()
        main_window._toggle_max_restore()
        assert main_window._shadow_effect is not None
        assert main_window._shadow_effect.isEnabled()

    # Windows-specific: native DWM model assertions
    @pytest.mark.skipif(sys.platform != "win32", reason="Native DWM path is Win32 only")
    def test_no_frameless_hint_on_win32(self, main_window: MainWindow) -> None:
        assert not (main_window.windowFlags() & Qt.WindowType.FramelessWindowHint)

    @pytest.mark.skipif(sys.platform != "win32", reason="Native DWM path is Win32 only")
    def test_no_translucent_background_on_win32(self, main_window: MainWindow) -> None:
        assert not main_window.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    @pytest.mark.skipif(sys.platform != "win32", reason="Native DWM path is Win32 only")
    def test_no_shadow_effect_on_win32(self, main_window: MainWindow) -> None:
        assert main_window._shadow_effect is None


# ---------------------------------------------------------------------------
# JWE-34: Language toggle (replaces old lang_btn tests)
# ---------------------------------------------------------------------------


class TestLanguageToggle:
    """DE/EN segmented toggle flips _lang and retranslates all section widgets."""

    def test_click_en_sets_lang_en(self, main_window: MainWindow) -> None:
        assert main_window._lang == "de"
        main_window.title_bar.en_btn.click()
        assert main_window._lang == "en"

    def test_click_de_from_en_sets_lang_de(self, qtbot, isolated_settings: QSettings) -> None:
        w = MainWindow(initial_lang="en", _settings=isolated_settings)
        qtbot.addWidget(w)
        w.title_bar.de_btn.click()
        assert w._lang == "de"

    def test_clicking_same_lang_is_noop(self, main_window: MainWindow) -> None:
        received: list[str] = []
        main_window.language_changed.connect(received.append)
        main_window.title_bar.de_btn.click()  # already "de"
        assert received == []

    def test_calls_retranslate_ui_on_all_five_widgets(self, main_window: MainWindow) -> None:
        with (
            patch.object(main_window.auth_widget, "retranslate_ui") as m_auth,
            patch.object(main_window.user_search_widget, "retranslate_ui") as m_user,
            patch.object(main_window.filter_widget, "retranslate_ui") as m_filter,
            patch.object(main_window.output_widget, "retranslate_ui") as m_output,
            patch.object(main_window.status_widget, "retranslate_ui") as m_status,
        ):
            main_window.title_bar.en_btn.click()

        m_auth.assert_called_once_with("en")
        m_user.assert_called_once_with("en")
        m_filter.assert_called_once_with("en")
        m_output.assert_called_once_with("en")
        m_status.assert_called_once_with("en")

    def test_language_changed_signal_emitted(self, main_window: MainWindow) -> None:
        received: list[str] = []
        main_window.language_changed.connect(received.append)
        main_window.title_bar.en_btn.click()
        assert received == ["en"]

    def test_de_btn_active_on_init(self, main_window: MainWindow) -> None:
        assert main_window.title_bar.de_btn.property("active") is True

    def test_en_btn_not_active_on_init(self, main_window: MainWindow) -> None:
        assert main_window.title_bar.en_btn.property("active") is False

    def test_en_btn_active_after_lang_switch(self, main_window: MainWindow) -> None:
        main_window.title_bar.en_btn.click()
        assert main_window.title_bar.en_btn.property("active") is True
        assert main_window.title_bar.de_btn.property("active") is False

    def test_lang_persisted_to_qsettings(self, qtbot, tmp_path: Path) -> None:
        settings_file = str(tmp_path / "lang_test.ini")
        s1 = QSettings(settings_file, QSettings.Format.IniFormat)
        w1 = MainWindow(_settings=s1)
        qtbot.addWidget(w1)
        w1.title_bar.en_btn.click()
        w1.close()
        s1.sync()

        s2 = QSettings(settings_file, QSettings.Format.IniFormat)
        w2 = MainWindow(_settings=s2)
        qtbot.addWidget(w2)
        assert w2._lang == "en"


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
# Export button integration -- Stage 4
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
        main_window.filter_widget.from_date.setDate(QDate(2025, 2, 15))
        main_window.filter_widget.to_date.setDate(QDate(2025, 1, 15))
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
    def test_saves_and_restores_filter_project_keys(self, qtbot, tmp_path: Path) -> None:
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

    def test_saves_and_restores_output_dir(self, qtbot, tmp_path: Path) -> None:
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

    def test_export_thread_stopped_after_close(self, qtbot, isolated_settings: QSettings) -> None:
        mock_svc = MagicMock()
        mock_svc.load_token.return_value = None
        w = MainWindow(_settings=isolated_settings, service=mock_svc)
        qtbot.addWidget(w)

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
    def test_search_fn_is_none_before_connection_verified(self, main_window: MainWindow) -> None:
        assert main_window.user_search_widget._search_worker._search_fn is None

    # MW-1: after connection_verified signal, _search_fn is set on the worker
    def test_search_fn_set_after_connection_verified(self, main_window: MainWindow) -> None:
        main_window.auth_widget.connection_verified.emit(_SA_CONFIG)
        assert main_window.user_search_widget._search_worker._search_fn is not None

    # MW-2: after connection_invalidated, _search_fn on the worker is None again
    def test_search_fn_cleared_after_connection_invalidated(self, main_window: MainWindow) -> None:
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


# ---------------------------------------------------------------------------
# JWE-50: TitleBar.set_maximized icon toggle
# ---------------------------------------------------------------------------


class TestTitleBarSetMaximized:
    """set_maximized swaps win_max_btn between the maximize and restore icons."""

    def test_initial_state_is_not_maximized(self, main_window: MainWindow) -> None:
        # Control buttons carry icons, not text glyphs.
        assert main_window.title_bar._is_maximized is False
        assert main_window.title_bar.win_max_btn.text() == ""

    def test_set_maximized_true_sets_is_maximized(self, main_window: MainWindow) -> None:
        main_window.title_bar.set_maximized(True)
        assert main_window.title_bar._is_maximized is True

    def test_set_maximized_false_clears_is_maximized(self, main_window: MainWindow) -> None:
        main_window.title_bar.set_maximized(True)
        main_window.title_bar.set_maximized(False)
        assert main_window.title_bar._is_maximized is False

    def test_toggle_max_restore_updates_icon_state_on_win32(self, main_window: MainWindow) -> None:
        if sys.platform != "win32":
            pytest.skip("Native maximize icon toggle is Win32 only")
        main_window._toggle_max_restore()
        assert main_window.title_bar._is_maximized is True
        main_window._toggle_max_restore()
        assert main_window.title_bar._is_maximized is False


# ---------------------------------------------------------------------------
# JWE-50: _nc_hit_region pure geometry (offscreen-safe, no Qt widget needed)
# ---------------------------------------------------------------------------

_WIN_W = 800
_WIN_H = 600
_TB_H = 44
_GRAB = 8

# Three simulated title-bar buttons (DE/EN/close) near the top-right.
# Kept below x=792 so they don't overlap the right-edge resize zone (_GRAB=8).
_BTN_RECTS = [
    QRect(720, 0, 20, _TB_H),
    QRect(740, 0, 20, _TB_H),
    QRect(760, 0, 20, _TB_H),
]
_WIN_SIZE = QSize(_WIN_W, _WIN_H)
_TB_RECT = QRect(0, 0, _WIN_W, _TB_H)


class TestNcHitRegion:
    """_nc_hit_region maps client-local points to WM_NCHITTEST codes (pure geometry)."""

    def _hit(self, x: int, y: int) -> int:
        return MainWindow._nc_hit_region(QPoint(x, y), _WIN_SIZE, _TB_RECT, _BTN_RECTS, _GRAB)

    def test_left_edge(self) -> None:
        assert self._hit(4, _WIN_H // 2) == _HTLEFT

    def test_right_edge(self) -> None:
        assert self._hit(_WIN_W - 4, _WIN_H // 2) == _HTRIGHT

    def test_top_edge(self) -> None:
        assert self._hit(_WIN_W // 2, 4) == _HTTOP

    def test_bottom_edge(self) -> None:
        assert self._hit(_WIN_W // 2, _WIN_H - 4) == _HTBOTTOM

    def test_top_left_corner(self) -> None:
        assert self._hit(4, 4) == _HTTOPLEFT

    def test_top_right_corner(self) -> None:
        assert self._hit(_WIN_W - 4, 4) == _HTTOPRIGHT

    def test_bottom_left_corner(self) -> None:
        assert self._hit(4, _WIN_H - 4) == _HTBOTTOMLEFT

    def test_bottom_right_corner(self) -> None:
        assert self._hit(_WIN_W - 4, _WIN_H - 4) == _HTBOTTOMRIGHT

    def test_caption_center(self) -> None:
        # Center of title bar, clear of buttons and all edges
        assert self._hit(200, _TB_H // 2) == _HTCAPTION

    def test_button_area_returns_htclient(self) -> None:
        # Inside last button rect (QRect(760, 0, 20, 44)) → HTCLIENT
        assert self._hit(770, 22) == _HTCLIENT

    def test_interior_below_titlebar_returns_htclient(self) -> None:
        assert self._hit(_WIN_W // 2, _WIN_H // 2) == _HTCLIENT

    def test_top_edge_overrides_caption(self) -> None:
        # Within title-bar height AND within top grab zone → edge wins
        assert self._hit(200, 4) == _HTTOP

    def test_button_overrides_edge(self) -> None:
        # Button at top-left corner — button check runs before edge check
        near_edge_btn = [QRect(0, 0, 20, 20)]
        result = MainWindow._nc_hit_region(QPoint(5, 5), _WIN_SIZE, _TB_RECT, near_edge_btn, _GRAB)
        assert result == _HTCLIENT

    def test_not_in_any_button_not_in_edge_not_in_caption_returns_htclient(self) -> None:
        # Below title bar, no edges → HTCLIENT
        assert self._hit(400, 200) == _HTCLIENT

    def test_right_edge_boundary_exact(self) -> None:
        # x == _WIN_W - _GRAB is the first pixel in the right zone
        assert self._hit(_WIN_W - _GRAB, _WIN_H // 2) == _HTRIGHT

    def test_just_inside_right_edge_boundary(self) -> None:
        # x == _WIN_W - _GRAB - 1 is just outside the right zone (interior)
        assert self._hit(_WIN_W - _GRAB - 1, _WIN_H // 2) == _HTCLIENT


# ---------------------------------------------------------------------------
# JWE-49: _edge_at_pos geometry (offscreen-safe, pure geometry test)
# ---------------------------------------------------------------------------


class TestEdgeAtPos:
    """_edge_at_pos detects edges and corners against the window outer rect."""

    def test_left_edge_mid(self, main_window: MainWindow) -> None:
        r = main_window.rect()
        edges = main_window._edge_at_pos(QPoint(2, r.height() // 2))
        assert edges == Qt.Edge.LeftEdge

    def test_right_edge_mid(self, main_window: MainWindow) -> None:
        r = main_window.rect()
        edges = main_window._edge_at_pos(QPoint(r.right() - 2, r.height() // 2))
        assert edges == Qt.Edge.RightEdge

    def test_top_edge_mid(self, main_window: MainWindow) -> None:
        r = main_window.rect()
        edges = main_window._edge_at_pos(QPoint(r.width() // 2, 2))
        assert edges == Qt.Edge.TopEdge

    def test_bottom_edge_mid(self, main_window: MainWindow) -> None:
        r = main_window.rect()
        edges = main_window._edge_at_pos(QPoint(r.width() // 2, r.bottom() - 2))
        assert edges == Qt.Edge.BottomEdge

    def test_top_left_corner(self, main_window: MainWindow) -> None:
        edges = main_window._edge_at_pos(QPoint(2, 2))
        assert edges is not None
        assert bool(edges & Qt.Edge.TopEdge)
        assert bool(edges & Qt.Edge.LeftEdge)

    def test_top_right_corner(self, main_window: MainWindow) -> None:
        r = main_window.rect()
        edges = main_window._edge_at_pos(QPoint(r.right() - 2, 2))
        assert edges is not None
        assert bool(edges & Qt.Edge.TopEdge)
        assert bool(edges & Qt.Edge.RightEdge)

    def test_bottom_left_corner(self, main_window: MainWindow) -> None:
        r = main_window.rect()
        edges = main_window._edge_at_pos(QPoint(2, r.bottom() - 2))
        assert edges is not None
        assert bool(edges & Qt.Edge.BottomEdge)
        assert bool(edges & Qt.Edge.LeftEdge)

    def test_bottom_right_corner(self, main_window: MainWindow) -> None:
        r = main_window.rect()
        edges = main_window._edge_at_pos(QPoint(r.right() - 2, r.bottom() - 2))
        assert edges is not None
        assert bool(edges & Qt.Edge.BottomEdge)
        assert bool(edges & Qt.Edge.RightEdge)

    def test_interior_returns_none(self, main_window: MainWindow) -> None:
        r = main_window.rect()
        edges = main_window._edge_at_pos(QPoint(r.width() // 2, r.height() // 2))
        assert edges is None
