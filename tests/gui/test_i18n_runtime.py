"""Runtime language-switch and persistence tests for Etappe 6 (JWE-2).

Two-channel i18n proof:
- Presentation strings (STRINGS / t()) change on language toggle.
- Diagnostic strings (DIAGNOSTICS / diag()) are locale-invariant.
- Language choice persists across MainWindow reconstruction via QSettings.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSettings, Qt

from jwe.gui.main_window import MainWindow
from jwe.i18n import diag, t


class TestRuntimeLanguageSwitch:
    """Language toggle updates all presentation texts; diagnostic texts are unchanged."""

    def test_presentation_texts_change_on_toggle(
        self, qtbot, main_window: MainWindow
    ) -> None:
        # Fixture starts in "de".
        assert main_window._lang == "de"

        auth_title_de = main_window.auth_widget.title()
        export_btn_de = main_window.status_widget.export_btn.text()
        counter_de = main_window.status_widget.issue_label.text()
        placeholder_de = main_window.user_search_widget.search_field.placeholderText()

        qtbot.mouseClick(main_window.lang_btn, Qt.MouseButton.LeftButton)
        assert main_window._lang == "en"

        assert main_window.auth_widget.title() == t("section.auth.title", "en")
        assert main_window.status_widget.export_btn.text() == t("status.btn.export", "en")
        assert main_window.status_widget.issue_label.text() == t(
            "status.counter.issues_n", "en", n=0
        )
        assert main_window.user_search_widget.search_field.placeholderText() == t(
            "user_search.search.placeholder", "en"
        )

        # Each changed — German != English for all four.
        assert main_window.auth_widget.title() != auth_title_de
        assert main_window.status_widget.export_btn.text() != export_btn_de
        assert main_window.status_widget.issue_label.text() != counter_de
        assert main_window.user_search_widget.search_field.placeholderText() != placeholder_de

    def test_diagnostic_text_invariant_on_toggle(
        self, qtbot, main_window: MainWindow
    ) -> None:
        """diag() strings are locale-invariant — the two-channel design proof."""
        assert main_window._lang == "de"
        diag_before = diag("status.log.cancelled")

        qtbot.mouseClick(main_window.lang_btn, Qt.MouseButton.LeftButton)
        assert main_window._lang == "en"
        diag_after = diag("status.log.cancelled")

        # Same English text regardless of window locale.
        assert diag_before == diag_after
        assert "cancelled" in diag_before.lower()


class TestLanguagePersistence:
    """Language choice is saved to QSettings on close and restored on reconstruction."""

    def test_lang_persists_across_reconstruction(
        self, qtbot, tmp_path: Path
    ) -> None:
        settings_file = str(tmp_path / "settings.ini")

        s1 = QSettings(settings_file, QSettings.Format.IniFormat)
        w1 = MainWindow(_settings=s1)
        qtbot.addWidget(w1)
        assert w1._lang == "de"

        # Toggle to English.
        qtbot.mouseClick(w1.lang_btn, Qt.MouseButton.LeftButton)
        assert w1._lang == "en"

        # closeEvent calls _save_settings, which writes lang = "en".
        w1.close()
        s1.sync()

        s2 = QSettings(settings_file, QSettings.Format.IniFormat)
        w2 = MainWindow(_settings=s2)
        qtbot.addWidget(w2)
        assert w2._lang == "en"
