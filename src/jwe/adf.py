"""Atlassian Document Format (ADF) → plain text conversion.

ADF is a JSON tree representation of rich text used by Jira Cloud REST API v3.
Worklog comments arrive as ADF; we flatten them to readable plain text for
the CSV column ``work_description``.

Strategy:
- ``text`` nodes contribute their ``text`` field.
- ``hardBreak`` adds ``\\n``.
- Block-level nodes (``paragraph``, ``heading``) end with ``\\n``.
- ``codeBlock`` is wrapped in triple backticks so it remains recognisable in CSV.
- ``rule`` renders as ``\\n---\\n`` (visible separator, not just a blank line).
- ``bulletList`` prefixes each item with ``- ``; ``orderedList`` with ``N. ``.
- Nested lists are indented by two spaces per depth level.
- ``mention`` renders as ``attrs.text`` (already ``@DisplayName``), falling
  back to ``attrs.id`` if ``text`` is absent or empty.
- ``inlineCard`` renders as ``attrs.url``, or empty string if absent.
- ``blockquote`` recurses into its children without extra markup.
- Unknown node types recurse into ``content`` without adding their own markup.
- Trailing whitespace is stripped from the final result.

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
    """
    if node is None:
        return ""
    return _render(node, list_depth=0).rstrip()


def _render(node: Any, list_depth: int = 0) -> str:
    if not isinstance(node, dict):  # pragma: no cover
        return ""

    match node.get("type"):
        case "text":
            return str(node.get("text", ""))
        case "hardBreak":
            return "\n"
        case "rule":
            return "\n---\n"
        case "mention":
            attrs: dict[str, Any] = node.get("attrs") or {}
            display = str(attrs.get("text", ""))
            return display if display else str(attrs.get("id", ""))
        case "inlineCard":
            ic_attrs: dict[str, Any] = node.get("attrs") or {}
            return str(ic_attrs.get("url", ""))
        case "doc" | "blockquote":
            return _join_children(node, list_depth)
        case "paragraph" | "heading":
            return _join_children(node, list_depth) + "\n"
        case "codeBlock":
            return "```\n" + _join_children(node, list_depth) + "\n```\n"
        case "bulletList":
            indent = "  " * list_depth
            parts: list[str] = [
                indent + "- " + _render_listitem(it, list_depth)
                for it in (node.get("content") or [])
            ]
            return "\n".join(parts) + "\n"
        case "orderedList":
            indent = "  " * list_depth
            parts = [
                indent + f"{i}. " + _render_listitem(it, list_depth)
                for i, it in enumerate(node.get("content") or [], 1)
            ]
            return "\n".join(parts) + "\n"
        case _:
            return _join_children(node, list_depth)


def _join_children(node: Any, list_depth: int) -> str:
    parts: list[str] = [_render(child, list_depth) for child in (node.get("content") or [])]
    return "".join(parts)


def _render_listitem(item: Any, list_depth: int) -> str:
    """Render the children of a listItem, stripping its trailing newline."""
    if not isinstance(item, dict):  # pragma: no cover
        return ""
    parts: list[str] = [_render(child, list_depth + 1) for child in (item.get("content") or [])]
    return "".join(parts).rstrip("\n")
