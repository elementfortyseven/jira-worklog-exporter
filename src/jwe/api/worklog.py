"""Wrapper for the Jira Cloud issue-worklog endpoint.

Uses ``GET /rest/api/3/issue/{issueIdOrKey}/worklog`` with offset/limit
pagination (``startAt``/``maxResults``). Note this is a *different* pagination
mechanism than the search endpoint's ``nextPageToken``.

The ``startedAfter`` and ``startedBefore`` query params take **Unix epoch
milliseconds** and let the server pre-filter by worklog date — this is much
faster than fetching everything and filtering client-side, especially for
issues with hundreds of worklogs.

TODO (claude code):
1. Implement :func:`iter_worklogs` with ``startAt``/``maxResults`` pagination.
2. Convert dates to epoch-ms for the server-side filter; document timezone
   semantics (Jira evaluates the filter in the calling user's TZ).
3. Apply a client-side safety filter: only yield worklogs whose
   ``author.accountId`` is in the requested set. This guards against any
   surprises from JQL-vs-worklog-author mismatches.
4. The comment field is in ADF (API v3) — yield it as-is; flatten in the
   exporter via :mod:`jwe.adf`.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import date
from typing import Any

from jwe.api.client import JiraCloudClient


@dataclass(frozen=True)
class Worklog:
    """A single worklog entry.

    Attributes:
        id: Worklog ID (string for API stability).
        issue_key: Parent issue key.
        author_account_id: Author's Atlassian account ID.
        author_display_name: Author's display name.
        author_email: Author's email if visible to the caller; else empty.
        started: ISO-8601 timestamp string when the work started.
        time_spent: Human-readable duration, e.g. ``"1h 30m"``.
        time_spent_seconds: Duration in seconds.
        comment_adf: Raw ADF tree for the comment, or ``None`` if absent.
        created: ISO-8601 creation timestamp.
        updated: ISO-8601 update timestamp.
    """

    id: str
    issue_key: str
    author_account_id: str
    author_display_name: str
    author_email: str
    started: str
    time_spent: str
    time_spent_seconds: int
    comment_adf: Any | None
    created: str
    updated: str


def iter_worklogs(
    client: JiraCloudClient,
    issue_key: str,
    from_date: date,
    to_date: date,
    account_ids: set[str],
    page_size: int = 1000,
) -> Iterator[Worklog]:
    """Yield worklogs of ``issue_key`` from ``from_date`` to ``to_date``.

    Args:
        client: Authenticated client.
        issue_key: Issue key (e.g. ``PROJ-123``).
        from_date: Inclusive lower bound on worklog start date.
        to_date: Inclusive upper bound on worklog start date.
        account_ids: Worklogs whose author isn't in this set are skipped
            (defense-in-depth alongside the JQL-level filter).
        page_size: Worklog pagination size (max 1000 per Atlassian docs).

    Yields:
        :class:`Worklog` instances matching the filter.

    TODO: implement. Convert dates → epoch-ms; paginate; filter; map JSON to
    the Worklog dataclass. See CLAUDE.md §7 step 6.
    """
    raise NotImplementedError("Implement iter_worklogs — see CLAUDE.md §7 step 6")
    yield  # pragma: no cover
