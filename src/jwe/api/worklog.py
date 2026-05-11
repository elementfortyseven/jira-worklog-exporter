"""Wrapper for the Jira Cloud issue-worklog endpoint.

Uses ``GET /rest/api/3/issue/{issueIdOrKey}/worklog`` with offset/limit
pagination (``startAt``/``maxResults``). Note this is a *different* pagination
mechanism than the search endpoint's ``nextPageToken``.

The ``startedAfter`` and ``startedBefore`` query params take **Unix epoch
milliseconds** and let the server pre-filter by worklog date — this is much
faster than fetching everything and filtering client-side, especially for
issues with hundreds of worklogs.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import date, datetime, time
from typing import Any

from jwe.api.client import JiraCloudClient

logger = logging.getLogger(__name__)

_WORKLOG_PATH = "/rest/api/3/issue/{issue_key}/worklog"


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


def _to_epoch_ms(d: date, t: time) -> int:
    # Uses system timezone — consistent with Jira's calling-user-timezone
    # behavior for worklogDate JQL filters.
    return int(datetime.combine(d, t).timestamp() * 1000)


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
    """
    started_after = _to_epoch_ms(from_date, time(0, 0, 0))
    started_before = _to_epoch_ms(to_date, time(23, 59, 59, 999000))
    path = _WORKLOG_PATH.format(issue_key=issue_key)
    start_at = 0

    while True:
        data: dict[str, Any] = client.request(
            "GET",
            path,
            params={
                "startAt": start_at,
                "maxResults": page_size,
                "startedAfter": started_after,
                "startedBefore": started_before,
            },
        )
        worklogs: list[dict[str, Any]] = data.get("worklogs", [])
        total: int = data.get("total", 0)
        logger.debug(
            "worklog page for %s: startAt=%d, got=%d, total=%d",
            issue_key,
            start_at,
            len(worklogs),
            total,
        )

        for wl in worklogs:
            author: dict[str, Any] = wl["author"]
            if author["accountId"] not in account_ids:
                continue
            yield Worklog(
                id=str(wl["id"]),
                issue_key=issue_key,
                author_account_id=author["accountId"],
                author_display_name=author["displayName"],
                author_email=author.get("emailAddress", ""),
                started=wl["started"],
                time_spent=wl["timeSpent"],
                time_spent_seconds=int(wl["timeSpentSeconds"]),
                comment_adf=wl.get("comment"),
                created=wl["created"],
                updated=wl["updated"],
            )

        # Double exit condition: last page detected by length OR total count.
        # Defense-in-depth against inaccurate total fields in the response.
        if len(worklogs) < page_size or start_at + len(worklogs) >= total:
            break

        start_at += len(worklogs)
