"""Tests for OutputWidget -- Stage 4."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from PySide6.QtCore import QSettings

from jwe.config import ColumnProfile
from jwe.gui.widgets.output import _DEFAULT_OUTPUT_DIR, OutputWidget

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def widget(qtbot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> OutputWidget:
    """OutputWidget created in an isolated temp directory so ./exports goes there."""
    monkeypatch.chdir(tmp_path)
    w = OutputWidget()
    qtbot.addWidget(w)
    return w


@pytest.fixture
def isolated_settings(tmp_path: Path) -> QSettings:
    return QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)


# ---------------------------------------------------------------------------
# Field presence
# ---------------------------------------------------------------------------


class TestFieldPresence:
    def test_has_output_dir_field(self, widget: OutputWidget) -> None:
        assert hasattr(widget, "output_dir_field")

    def test_has_browse_btn(self, widget: OutputWidget) -> None:
        assert hasattr(widget, "browse_btn")

    def test_has_delimiter_combo(self, widget: OutputWidget) -> None:
        assert hasattr(widget, "delimiter_combo")

    def test_has_column_profile_combo(self, widget: OutputWidget) -> None:
        assert hasattr(widget, "column_profile_combo")

    def test_has_api_version_combo(self, widget: OutputWidget) -> None:
        assert hasattr(widget, "api_version_combo")


# ---------------------------------------------------------------------------
# Default values
# ---------------------------------------------------------------------------


class TestDefaultValues:
    def test_output_dir_default_is_exports_path(self, widget: OutputWidget) -> None:
        assert widget.output_dir_field.text() == _DEFAULT_OUTPUT_DIR

    def test_delimiter_default_is_comma(self, widget: OutputWidget) -> None:
        assert widget.delimiter_combo.currentData() == ","

    def test_column_profile_default_is_standard(self, widget: OutputWidget) -> None:
        assert widget.column_profile_combo.currentData() == ColumnProfile.STANDARD.value

    def test_api_version_default_is_3(self, widget: OutputWidget) -> None:
        assert widget.api_version_combo.currentData() == 3


# ---------------------------------------------------------------------------
# Auto-create output dir
# ---------------------------------------------------------------------------


class TestAutoCreateOutputDir:
    def test_default_exports_dir_created_on_init(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, qtbot
    ) -> None:
        monkeypatch.chdir(tmp_path)
        w = OutputWidget()
        qtbot.addWidget(w)
        assert (tmp_path / "exports").is_dir()

    def test_manually_typed_nonexistent_dir_does_not_auto_create(
        self, widget: OutputWidget, tmp_path: Path
    ) -> None:
        nonexistent = str(tmp_path / "does_not_exist")
        widget.output_dir_field.setText(nonexistent)
        assert not Path(nonexistent).exists()


# ---------------------------------------------------------------------------
# is_valid
# ---------------------------------------------------------------------------


class TestIsValid:
    def test_valid_when_output_dir_exists(self, widget: OutputWidget, tmp_path: Path) -> None:
        widget.output_dir_field.setText(str(tmp_path))
        assert widget.is_valid() is True

    def test_invalid_when_output_dir_does_not_exist(
        self, widget: OutputWidget, tmp_path: Path
    ) -> None:
        widget.output_dir_field.setText(str(tmp_path / "ghost"))
        assert widget.is_valid() is False

    def test_invalid_when_output_dir_field_is_empty(self, widget: OutputWidget) -> None:
        widget.output_dir_field.setText("")
        assert widget.is_valid() is False

    def test_valid_after_setting_existing_dir(self, widget: OutputWidget, tmp_path: Path) -> None:
        widget.output_dir_field.setText(str(tmp_path / "ghost"))
        assert widget.is_valid() is False
        widget.output_dir_field.setText(str(tmp_path))
        assert widget.is_valid() is True


# ---------------------------------------------------------------------------
# validation_changed signal
# ---------------------------------------------------------------------------


class TestValidationChangedSignal:
    def test_emitted_on_dir_change(self, qtbot, widget: OutputWidget, tmp_path: Path) -> None:
        with qtbot.waitSignal(widget.validation_changed, timeout=500):
            widget.output_dir_field.setText(str(tmp_path))

    def test_not_emitted_when_dir_field_unchanged(self, widget: OutputWidget) -> None:
        signals: list[None] = []
        widget.validation_changed.connect(lambda: signals.append(None))
        current = widget.output_dir_field.text()
        widget.output_dir_field.setText(current)
        assert len(signals) == 0


# ---------------------------------------------------------------------------
# Browse button
# ---------------------------------------------------------------------------


class TestBrowseButton:
    def test_browse_btn_opens_file_dialog(self, qtbot, widget: OutputWidget) -> None:
        with patch(
            "jwe.gui.widgets.output.QFileDialog.getExistingDirectory",
            return_value="",
        ) as mock_dialog:
            qtbot.mouseClick(
                widget.browse_btn,
                __import__("PySide6.QtCore", fromlist=["Qt"]).Qt.MouseButton.LeftButton,
            )
            mock_dialog.assert_called_once()

    def test_browse_btn_sets_path_on_accept(
        self, qtbot, widget: OutputWidget, tmp_path: Path
    ) -> None:
        chosen = str(tmp_path / "chosen_dir")
        Path(chosen).mkdir()
        with patch(
            "jwe.gui.widgets.output.QFileDialog.getExistingDirectory",
            return_value=chosen,
        ):
            qtbot.mouseClick(
                widget.browse_btn,
                __import__("PySide6.QtCore", fromlist=["Qt"]).Qt.MouseButton.LeftButton,
            )
        assert widget.output_dir_field.text() == chosen

    def test_browse_btn_does_not_change_path_on_cancel(self, qtbot, widget: OutputWidget) -> None:
        original = widget.output_dir_field.text()
        with patch(
            "jwe.gui.widgets.output.QFileDialog.getExistingDirectory",
            return_value="",
        ):
            qtbot.mouseClick(
                widget.browse_btn,
                __import__("PySide6.QtCore", fromlist=["Qt"]).Qt.MouseButton.LeftButton,
            )
        assert widget.output_dir_field.text() == original


# ---------------------------------------------------------------------------
# QSettings roundtrip
# ---------------------------------------------------------------------------


class TestQSettings:
    def test_output_dir_roundtrip(
        self, widget: OutputWidget, isolated_settings: QSettings, tmp_path: Path
    ) -> None:
        target = str(tmp_path)
        widget.output_dir_field.setText(target)
        widget.save_settings(isolated_settings)
        widget.output_dir_field.setText("")
        widget.load_settings(isolated_settings)
        assert widget.output_dir_field.text() == target

    def test_delimiter_roundtrip(self, widget: OutputWidget, isolated_settings: QSettings) -> None:
        widget.delimiter_combo.setCurrentIndex(widget.delimiter_combo.findData(";"))
        widget.save_settings(isolated_settings)
        widget.delimiter_combo.setCurrentIndex(0)
        widget.load_settings(isolated_settings)
        assert widget.delimiter_combo.currentData() == ";"

    def test_column_profile_roundtrip(
        self, widget: OutputWidget, isolated_settings: QSettings
    ) -> None:
        widget.column_profile_combo.setCurrentIndex(
            widget.column_profile_combo.findData(ColumnProfile.FULL.value)
        )
        widget.save_settings(isolated_settings)
        widget.column_profile_combo.setCurrentIndex(0)
        widget.load_settings(isolated_settings)
        assert widget.column_profile_combo.currentData() == ColumnProfile.FULL.value

    def test_api_version_roundtrip(
        self, widget: OutputWidget, isolated_settings: QSettings
    ) -> None:
        widget.api_version_combo.setCurrentIndex(widget.api_version_combo.findData(2))
        widget.save_settings(isolated_settings)
        widget.api_version_combo.setCurrentIndex(0)
        widget.load_settings(isolated_settings)
        assert widget.api_version_combo.currentData() == 2


# ---------------------------------------------------------------------------
# JWE-36: [invalid] property and browse_btn width
# ---------------------------------------------------------------------------


class TestInvalidProperty:
    def test_nonexistent_path_marks_dir_field_invalid(
        self, widget: OutputWidget, tmp_path: Path
    ) -> None:
        widget.output_dir_field.setText(str(tmp_path / "ghost"))
        assert widget.output_dir_field.property("invalid") is True

    def test_existing_path_clears_invalid(self, widget: OutputWidget, tmp_path: Path) -> None:
        widget.output_dir_field.setText(str(tmp_path / "ghost"))
        widget.output_dir_field.setText(str(tmp_path))
        assert not widget.output_dir_field.property("invalid")

    def test_empty_path_not_marked_invalid(self, widget: OutputWidget) -> None:
        # Empty is handled by is_valid() returning False; no red border on blank.
        widget.output_dir_field.setText("some")
        widget.output_dir_field.setText("")
        assert not widget.output_dir_field.property("invalid")

    def test_browse_btn_width_unrestricted(self, widget: OutputWidget) -> None:
        assert widget.browse_btn.maximumWidth() > 80
