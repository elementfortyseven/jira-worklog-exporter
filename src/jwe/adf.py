"""Atlassian Document Format (ADF) → plain text conversion.

ADF is a JSON tree representation of rich text used by Jira Cloud REST API v3.
Worklog comments arrive as ADF; we flatten them to readable plain text for
the CSV column ``work_description``.

TODO (claude code):
1. Implement :func:`adf_to_text` as a recursive walker over node types.
2. Cover at minimum: ``doc``, ``paragraph``, ``text``, ``hardBreak``,
   ``bulletList``, ``orderedList``, ``listItem``, ``mention``, ``inlineCard``,
   ``codeBlock``, ``heading``, ``blockquote``, ``rule``.
3. Use the fixture ``tests/fixtures/adf_samples.json`` to drive your tests.
   Each sample documents the expected plain-text rendering.
4. Strategy:
   - ``text`` nodes contribute their ``text`` field.
   - ``hardBreak`` adds ``\\n``.
   - Block-level nodes (``paragraph``, ``heading``) end with ``\\n``.
   - ``listItem`` prefixes its content with ``- `` for bullets and
     ``1. `` (or ``N. ``) for ordered.
   - ``mention`` renders as ``@DisplayName``.
   - ``inlineCard`` renders as the URL (or empty if absent).
   - ``codeBlock`` content is dumped as-is.
   - Trim trailing whitespace at the end.

The result is a single string, with ``\\n`` separating lines.
"""

from __future__ import annotations

from typing import Any


def adf_to_text(node: Any) -> str:
    """Convert an ADF tree (or sub-tree, or ``None``) to plain text.

    Args:
        node: Any ADF node — typically a top-level ``doc`` node, or ``None``
            if the comment is absent.

    Returns:
        A plain-text rendering. Empty string if ``node`` is ``None`` or empty.

    TODO: implement. See module docstring for strategy and CLAUDE.md §4.
    """
    if node is None:
        return ""
    raise NotImplementedError("Implement adf_to_text — see CLAUDE.md §7 step 3")
