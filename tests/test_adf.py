"""Tests for jwe.adf."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from jwe.adf import adf_to_text

FIXTURES_DIR = Path(__file__).parent / "fixtures"
SAMPLES: list[dict[str, Any]] = json.loads(
    (FIXTURES_DIR / "adf_samples.json").read_text(encoding="utf-8")
)
_BY_NAME: dict[str, dict[str, Any]] = {s["name"]: s for s in SAMPLES}


def _s(name: str) -> dict[str, Any]:
    return _BY_NAME[name]


# ---------------------------------------------------------------------------
# None guard — locked in before any implementation exists
# ---------------------------------------------------------------------------


def test_none_input_returns_empty_string() -> None:
    assert adf_to_text(None) == ""


# ---------------------------------------------------------------------------
# Parametrized regression sweep over every fixture sample
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("sample", SAMPLES, ids=[s["name"] for s in SAMPLES])
def test_fixture_sample(sample: dict[str, Any]) -> None:
    assert adf_to_text(sample["adf"]) == sample["expected"]


# ---------------------------------------------------------------------------
# Dedicated per-node-type tests (call fixtures by name for clear failures)
# ---------------------------------------------------------------------------


def test_empty_doc() -> None:
    s = _s("empty doc")
    assert adf_to_text(s["adf"]) == s["expected"]


def test_single_paragraph() -> None:
    s = _s("single paragraph plain text")
    assert adf_to_text(s["adf"]) == s["expected"]


def test_two_paragraphs_separated_by_newline() -> None:
    s = _s("two paragraphs separated by newline")
    assert adf_to_text(s["adf"]) == s["expected"]


def test_bullet_list() -> None:
    s = _s("bullet list")
    assert adf_to_text(s["adf"]) == s["expected"]


def test_ordered_list() -> None:
    s = _s("ordered list")
    assert adf_to_text(s["adf"]) == s["expected"]


def test_mention_rendered_as_display_name() -> None:
    s = _s("mention rendered as @DisplayName")
    assert adf_to_text(s["adf"]) == s["expected"]


def test_hard_break_inside_paragraph() -> None:
    s = _s("hard break inside paragraph")
    assert adf_to_text(s["adf"]) == s["expected"]


def test_inline_card_renders_as_url() -> None:
    s = _s("inline card renders as url")
    assert adf_to_text(s["adf"]) == s["expected"]


def test_code_block_wrapped_in_backticks() -> None:
    s = _s("code block with multi-line content")
    assert adf_to_text(s["adf"]) == s["expected"]


def test_heading_followed_by_paragraph() -> None:
    s = _s("heading followed by paragraph")
    assert adf_to_text(s["adf"]) == s["expected"]


def test_blockquote_renders_content_inline() -> None:
    s = _s("blockquote renders content inline")
    assert adf_to_text(s["adf"]) == s["expected"]


def test_rule_produces_visible_separator() -> None:
    s = _s("rule produces visible separator")
    assert adf_to_text(s["adf"]) == s["expected"]


# ---------------------------------------------------------------------------
# Negative / edge-case tests
# ---------------------------------------------------------------------------


def test_unknown_node_type_ignored_content_passes_through() -> None:
    node = {
        "type": "doc",
        "version": 1,
        "content": [
            {
                "type": "paragraph",
                "content": [
                    {"type": "text", "text": "before "},
                    {"type": "unknownWidget", "attrs": {}, "content": []},
                    {"type": "text", "text": "after"},
                ],
            }
        ],
    }
    assert adf_to_text(node) == "before after"


def test_nested_bullet_list_indents_two_spaces_per_level() -> None:
    node = {
        "type": "doc",
        "version": 1,
        "content": [
            {
                "type": "bulletList",
                "content": [
                    {
                        "type": "listItem",
                        "content": [
                            {
                                "type": "paragraph",
                                "content": [{"type": "text", "text": "Outer"}],
                            },
                            {
                                "type": "bulletList",
                                "content": [
                                    {
                                        "type": "listItem",
                                        "content": [
                                            {
                                                "type": "paragraph",
                                                "content": [{"type": "text", "text": "Inner"}],
                                            }
                                        ],
                                    }
                                ],
                            },
                        ],
                    }
                ],
            }
        ],
    }
    assert adf_to_text(node) == "- Outer\n  - Inner"


def test_mention_empty_text_falls_back_to_id() -> None:
    node = {
        "type": "doc",
        "version": 1,
        "content": [
            {
                "type": "paragraph",
                "content": [
                    {"type": "mention", "attrs": {"id": "557058:abc-def", "text": ""}}
                ],
            }
        ],
    }
    assert adf_to_text(node) == "557058:abc-def"
