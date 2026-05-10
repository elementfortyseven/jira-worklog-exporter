"""Tests for jwe.adf.

TODO (claude code): drive the implementation from the fixture file at
``tests/fixtures/adf_samples.json``. Each sample documents an input ADF tree
and the expected plain-text rendering. See CLAUDE.md §7 step 3.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from jwe.adf import adf_to_text

FIXTURES_DIR = Path(__file__).parent / "fixtures"
SAMPLES_PATH = FIXTURES_DIR / "adf_samples.json"


def test_none_input_returns_empty_string() -> None:
    """The only behaviour we can lock in before implementation: None → ''."""
    assert adf_to_text(None) == ""


@pytest.mark.skip(reason="adf_to_text not yet implemented")
def test_samples() -> None:
    """Drive every sample in the fixture through the converter."""
    samples = json.loads(SAMPLES_PATH.read_text(encoding="utf-8"))
    for sample in samples:
        assert adf_to_text(sample["adf"]) == sample["expected"], sample["name"]
