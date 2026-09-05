"""Offscreen tests for IdentityStrip (JWE-37)."""

from __future__ import annotations

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from jwe.gui.widgets.identity_strip import IdentityStrip

_NAME = "Bot User"
_ACCOUNT_ID = "5f8a2b1c-account-id-full-uuid-value"

# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def strip(qtbot) -> IdentityStrip:
    w = IdentityStrip()
    qtbot.addWidget(w)
    return w


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


class TestConstruction:
    def test_objectname_is_idstrip(self, strip: IdentityStrip) -> None:
        assert strip.objectName() == "idStrip"

    def test_hidden_by_default(self, strip: IdentityStrip) -> None:
        assert strip.isHidden()


# ---------------------------------------------------------------------------
# set_identity
# ---------------------------------------------------------------------------


class TestSetIdentity:
    def test_shows_the_strip(self, strip: IdentityStrip) -> None:
        strip.set_identity(_NAME, _ACCOUNT_ID)
        assert not strip.isHidden()

    def test_sets_label_text_with_name(self, strip: IdentityStrip) -> None:
        strip.set_identity(_NAME, _ACCOUNT_ID)
        assert _NAME in strip._label.text()

    def test_tooltip_contains_full_account_id(self, strip: IdentityStrip) -> None:
        strip.set_identity(_NAME, _ACCOUNT_ID)
        assert _ACCOUNT_ID in strip.toolTip()


# ---------------------------------------------------------------------------
# clear
# ---------------------------------------------------------------------------


class TestClear:
    def test_hides_the_strip(self, strip: IdentityStrip) -> None:
        strip.set_identity(_NAME, _ACCOUNT_ID)
        strip.clear()
        assert strip.isHidden()

    def test_clear_without_prior_identity_stays_hidden(self, strip: IdentityStrip) -> None:
        strip.clear()
        assert strip.isHidden()


# ---------------------------------------------------------------------------
# Click-to-copy
# ---------------------------------------------------------------------------


class TestClickToCopy:
    def test_click_copies_full_account_id_to_clipboard(self, qtbot, strip: IdentityStrip) -> None:
        strip.set_identity(_NAME, _ACCOUNT_ID)
        qtbot.mouseClick(strip, Qt.MouseButton.LeftButton)
        assert QApplication.clipboard().text() == _ACCOUNT_ID

    def test_click_shows_copied_confirmation_then_reverts(
        self, qtbot, strip: IdentityStrip
    ) -> None:
        strip.set_identity(_NAME, _ACCOUNT_ID)
        qtbot.mouseClick(strip, Qt.MouseButton.LeftButton)

        assert "Copied" in strip._label.text()
        qtbot.wait(1300)
        assert _NAME in strip._label.text()

    def test_click_with_no_identity_does_not_touch_clipboard(
        self, qtbot, strip: IdentityStrip
    ) -> None:
        QApplication.clipboard().setText("unrelated-sentinel")
        qtbot.mouseClick(strip, Qt.MouseButton.LeftButton)
        assert QApplication.clipboard().text() == "unrelated-sentinel"
