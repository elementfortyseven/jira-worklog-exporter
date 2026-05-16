"""Tests for MainWindow — Etappe 1 (skeleton)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from PySide6.QtCore import QByteArray, QSettings, Qt

from jwe.gui.main_window import MainWindow


class TestMainWindowInstantiates:
    """MainWindow can be created and shown without error."""

    def test_shows_without_error(self, qtbot, main_window: MainWindow) -> None:
        main_window.show()
        assert main_window.isVisible()

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
