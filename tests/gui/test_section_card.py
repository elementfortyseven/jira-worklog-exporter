"""Offscreen tests for SectionCard (JWE-35)."""

from __future__ import annotations

import pytest
from PySide6.QtWidgets import QLabel, QPushButton

from jwe.gui.widgets.section_card import SectionCard
from jwe.i18n import t

# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def card(qtbot) -> SectionCard:
    w = SectionCard("01", "plug", "section.auth.title", "section.auth.subtitle")
    qtbot.addWidget(w)
    return w


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


class TestConstruction:
    def test_objectname_is_sectioncard(self, card: SectionCard) -> None:
        assert card.objectName() == "sectionCard"

    def test_has_icon_label(self, card: SectionCard) -> None:
        assert hasattr(card, "_icon_label")
        assert isinstance(card._icon_label, QLabel)

    def test_icon_label_objectname(self, card: SectionCard) -> None:
        assert card._icon_label.objectName() == "sectionIcon"

    def test_icon_label_fixed_30x30(self, card: SectionCard) -> None:
        assert card._icon_label.width() == 30
        assert card._icon_label.height() == 30

    def test_has_index_label(self, card: SectionCard) -> None:
        assert hasattr(card, "_index_label")
        assert isinstance(card._index_label, QLabel)

    def test_index_label_objectname(self, card: SectionCard) -> None:
        assert card._index_label.objectName() == "sectionIndex"

    def test_index_label_contains_index(self, card: SectionCard) -> None:
        assert "01" in card._index_label.text()

    def test_has_title_label(self, card: SectionCard) -> None:
        assert hasattr(card, "_title_label")
        assert isinstance(card._title_label, QLabel)

    def test_title_label_objectname(self, card: SectionCard) -> None:
        assert card._title_label.objectName() == "sectionTitle"

    def test_has_subtitle_label(self, card: SectionCard) -> None:
        assert hasattr(card, "_subtitle_label")
        assert isinstance(card._subtitle_label, QLabel)

    def test_subtitle_label_objectname(self, card: SectionCard) -> None:
        assert card._subtitle_label.objectName() == "sectionSubtitle"

    def test_has_tick(self, card: SectionCard) -> None:
        assert hasattr(card, "_tick")
        assert card._tick.objectName() == "sectionTick"

    def test_tick_fixed_26x2(self, card: SectionCard) -> None:
        assert card._tick.width() == 26
        assert card._tick.height() == 2

    def test_has_head_end(self, card: SectionCard) -> None:
        assert hasattr(card, "_head_end")
        assert card._head_end.objectName() == "sectionHeadEnd"

    def test_default_title_is_en(self, card: SectionCard) -> None:
        assert card._title_label.text() == t("section.auth.title", "en")

    def test_default_subtitle_is_en(self, card: SectionCard) -> None:
        assert card._subtitle_label.text() == t("section.auth.subtitle", "en")


# ---------------------------------------------------------------------------
# retranslate_ui
# ---------------------------------------------------------------------------


class TestRetranslateUi:
    def test_title_updates_to_de(self, card: SectionCard) -> None:
        card.retranslate_ui("de")
        assert card._title_label.text() == t("section.auth.title", "de")

    def test_subtitle_updates_to_de(self, card: SectionCard) -> None:
        card.retranslate_ui("de")
        assert card._subtitle_label.text() == t("section.auth.subtitle", "de")

    def test_title_updates_back_to_en(self, card: SectionCard) -> None:
        card.retranslate_ui("de")
        card.retranslate_ui("en")
        assert card._title_label.text() == t("section.auth.title", "en")

    def test_de_title_differs_from_en_title(self, card: SectionCard) -> None:
        card.retranslate_ui("de")
        de_title = card._title_label.text()
        card.retranslate_ui("en")
        en_title = card._title_label.text()
        assert de_title != en_title


# ---------------------------------------------------------------------------
# title() helper
# ---------------------------------------------------------------------------


class TestTitleMethod:
    def test_title_returns_title_label_text(self, card: SectionCard) -> None:
        assert card.title() == card._title_label.text()

    def test_title_reflects_retranslate(self, card: SectionCard) -> None:
        card.retranslate_ui("de")
        assert card.title() == t("section.auth.title", "de")


# ---------------------------------------------------------------------------
# set_head_widget
# ---------------------------------------------------------------------------


class TestSetHeadWidget:
    def test_set_head_widget_hosts_widget(self, qtbot, card: SectionCard) -> None:
        btn = QPushButton("Test")
        qtbot.addWidget(btn)
        card.set_head_widget(btn)
        assert btn.parent() is card._head_end

    def test_set_head_widget_child_visible_in_head_end(self, qtbot, card: SectionCard) -> None:
        lbl = QLabel("slot")
        qtbot.addWidget(lbl)
        card.set_head_widget(lbl)
        found = card._head_end.findChildren(QLabel)
        assert lbl in found


# ---------------------------------------------------------------------------
# content_layout
# ---------------------------------------------------------------------------


class TestContentLayout:
    def test_content_layout_accepts_widget(self, qtbot, card: SectionCard) -> None:
        child = QLabel("content child")
        qtbot.addWidget(child)
        card.content_layout().addWidget(child)
        assert child.parent() is card._content
