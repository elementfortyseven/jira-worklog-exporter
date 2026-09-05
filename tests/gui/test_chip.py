"""Offscreen tests for Chip (JWE-37)."""

from __future__ import annotations

import pytest

from jwe.gui.widgets.chip import Chip

# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def chip(qtbot) -> Chip:
    w = Chip()
    qtbot.addWidget(w)
    return w


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


class TestConstruction:
    def test_objectname_is_chip(self, chip: Chip) -> None:
        assert chip.objectName() == "chip"

    def test_default_variant_is_neutral(self, chip: Chip) -> None:
        assert chip.property("variant") == "neutral"

    def test_default_dot_hidden(self, chip: Chip) -> None:
        assert chip._dot.isHidden()

    def test_default_spinner_hidden(self, chip: Chip) -> None:
        assert chip._spinner.isHidden()


# ---------------------------------------------------------------------------
# set_state
# ---------------------------------------------------------------------------


class TestSetState:
    def test_ok_sets_variant_property(self, chip: Chip) -> None:
        chip.set_state("ok", "Connected")
        assert chip.property("variant") == "ok"

    def test_ok_sets_uppercased_label(self, chip: Chip) -> None:
        chip.set_state("ok", "Connected")
        assert chip._label.text() == "CONNECTED"

    def test_ok_shows_dot(self, chip: Chip) -> None:
        chip.set_state("ok", "Connected")
        assert not chip._dot.isHidden()

    def test_ok_does_not_show_spinner(self, chip: Chip) -> None:
        chip.set_state("ok", "Connected")
        assert chip._spinner.isHidden()

    def test_testing_sets_variant_property(self, chip: Chip) -> None:
        chip.set_state("testing", "Testing")
        assert chip.property("variant") == "testing"

    def test_testing_shows_spinner(self, chip: Chip) -> None:
        chip.set_state("testing", "Testing")
        assert not chip._spinner.isHidden()

    def test_testing_does_not_show_dot(self, chip: Chip) -> None:
        chip.set_state("testing", "Testing")
        assert chip._dot.isHidden()

    def test_error_sets_variant_property(self, chip: Chip) -> None:
        chip.set_state("error", "Error")
        assert chip.property("variant") == "error"

    def test_error_shows_neither_indicator(self, chip: Chip) -> None:
        chip.set_state("error", "Error")
        assert chip._dot.isHidden()
        assert chip._spinner.isHidden()

    def test_switching_from_ok_to_testing_hides_dot(self, chip: Chip) -> None:
        chip.set_state("ok", "Connected")
        chip.set_state("testing", "Testing")
        assert chip._dot.isHidden()
        assert not chip._spinner.isHidden()
