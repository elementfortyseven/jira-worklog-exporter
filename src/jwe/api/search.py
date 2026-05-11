"""Wrapper for the Jira Cloud JQL search endpoint.

Uses ``POST /rest/api/3/search/jql`` with ``nextPageToken`` pagination — the
``GET /search`` endpoint is deprecated in Cloud.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import date
from typing import Any

from jwe.api.client import JiraCloudClient

logger = logging.getLogger(__name__)

_PROJECT_KEY_RE = re.compile(r"^[A-Z][A-Z0-9_]+$")
_SEARCH_PATH = "/rest/api/3/search/jql"
_SEARCH_FIELDS = ["summary", "project"]


@dataclass(frozen=True)
class IssueRef:
    """A minimal issue reference returned by JQL search.

    Attributes:
        key: Issue key, e.g. ``PROJ-123``.
        summary: Issue summary line.
        project_key: Project key, e.g. ``PROJ``.
        project_name: Human-readable project name.
    """

    key: str
    summary: str
    project_key: str
    project_name: str


def build_jql(
    account_ids: list[str],
    from_date: date,
    to_date: date,
    project_keys: list[str] | None = None,
) -> str:
    """Build a JQL string for the worklog search.

    Args:
        account_ids: Atlassian account IDs. Quoted in the output; embedded
            double-quotes are escaped.
        from_date: Inclusive lower bound on ``worklogDate``.
        to_date: Inclusive upper bound on ``worklogDate``.
        project_keys: Optional project filter; ``None`` or empty means no
            project restriction. Each key must match ``^[A-Z][A-Z0-9_]+$``.

    Returns:
        A JQL string suitable for ``POST /rest/api/3/search/jql``.

    Raises:
        ValueError: If ``account_ids`` is empty or any ``project_keys`` entry
            fails validation.
    """
    if not account_ids:
        raise ValueError("account_ids must not be empty")

    if project_keys is not None:
        for key in project_keys:
            if not _PROJECT_KEY_RE.match(key):
                raise ValueError(
                    f"Invalid project key {key!r}. Must match ^[A-Z][A-Z0-9_]+$"
                )

    def _quote_id(aid: str) -> str:
        return '"' + aid.replace('"', '\\"') + '"'

    author_list = ", ".join(_quote_id(aid) for aid in account_ids)
    clauses = [
        f"worklogAuthor in ({author_list})",
        f'worklogDate >= "{from_date.isoformat()}"',
        f'worklogDate <= "{to_date.isoformat()}"',
    ]
    if project_keys:
        clauses.append(f"project in ({', '.join(project_keys)})")

    return " AND ".join(clauses)


def iter_issues(
    client: JiraCloudClient,
    jql: str,
    page_size: int = 100,
) -> Iterator[IssueRef]:
    """Yield issue references matching ``jql``, paginating server-side.

    Args:
        client: Authenticated client.
        jql: A JQL string, typically built by :func:`build_jql`.
        page_size: Server-side page size hint. Atlassian caps this; treat as
            advisory.

    Yields:
        :class:`IssueRef` for each matching issue.
    """
    next_page_token: str | None = None

    while True:
        body: dict[str, Any] = {
            "jql": jql,
            "fields": _SEARCH_FIELDS,
            "maxResults": page_size,
        }
        if next_page_token is not None:
            body["nextPageToken"] = next_page_token

        data: dict[str, Any] = client.request("POST", _SEARCH_PATH, json=body)
        logger.debug("search page returned %d issues", len(data.get("issues", [])))

        for issue in data.get("issues", []):
            fields = issue.get("fields", {})
            project = fields.get("project", {})
            yield IssueRef(
                key=issue["key"],
                summary=fields.get("summary", ""),
                project_key=project.get("key", ""),
                project_name=project.get("name", ""),
            )

        next_page_token = data.get("nextPageToken")
        if next_page_token is None:
            break
