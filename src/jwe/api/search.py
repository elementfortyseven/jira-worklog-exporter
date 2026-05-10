"""Wrapper for the Jira Cloud JQL search endpoint.

Uses ``POST /rest/api/3/search/jql`` with ``nextPageToken`` pagination — the
``GET /search`` endpoint is deprecated in Cloud.

TODO (claude code):
1. Implement :func:`iter_issues` to paginate through results, yielding
   :class:`IssueRef` instances.
2. Request only the fields we actually need (``summary``, ``project``,
   ``issuetype``) — issuetype helps with debugging atypical worklog patterns.
3. Add a JQL builder helper :func:`build_jql` that quotes accountIds safely
   and joins date/project clauses. Keep it pure and test it heavily.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import date

from jwe.api.client import JiraCloudClient


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
        account_ids: Atlassian account IDs (cloud-form, with or without colon
            prefix). Quoted in the output.
        from_date: Inclusive lower bound on ``worklogDate``.
        to_date: Inclusive upper bound on ``worklogDate``.
        project_keys: Optional project filter; ``None`` or empty means no
            project restriction.

    Returns:
        A JQL string suitable for ``POST /rest/api/3/search/jql``.

    TODO: implement. See CLAUDE.md §5 for the exact form.
    """
    raise NotImplementedError("Implement build_jql — see CLAUDE.md §5")


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

    TODO: implement using ``client.request("POST", "/rest/api/3/search/jql", ...)``.
    Use ``nextPageToken`` for pagination; stop when the server omits it.
    """
    raise NotImplementedError("Implement iter_issues — see CLAUDE.md §5 and §7 step 5")
    yield  # pragma: no cover
