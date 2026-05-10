"""Tests for jwe.exporter.

TODO (claude code): drive the implementation from end-to-end mock scenarios.
Use ``responses`` to mock the full chain: /myself, /search/jql, /issue/X/worklog.
Verify the data flow in CLAUDE.md §4 produces the expected CSV rows.
"""

from __future__ import annotations

import pytest


@pytest.mark.skip(reason="exporter.run_export not yet implemented")
def test_dry_run_writes_no_file() -> None:
    """In dry-run mode, no CSV is created; counts are still reported."""
    raise AssertionError("placeholder — implement once exporter is built")
