"""Wrapper for the Jira Cloud user-search endpoint.

Uses ``GET /rest/api/3/user/search?query=<email-or-name>``. Cloud no longer
exposes usernames; lookups must produce ``accountId`` for downstream JQL.

TODO (claude code):
1. Implement :func:`search_users` with sensible defaults (``maxResults``
   capped to e.g. 50; user can paginate manually if needed).
2. Implement :func:`get_myself` returning the calling identity for the
   client's connection test.
3. Some emails are hidden by privacy settings; the response may omit
   ``emailAddress``. Treat it as optional in the dataclass.
"""

from __future__ import annotations

from dataclasses import dataclass

from jwe.api.client import JiraCloudClient


@dataclass(frozen=True)
class User:
    """A Jira user reference.

    Attributes:
        account_id: Stable account identifier.
        display_name: Display name.
        email: Email if visible; empty string if hidden by privacy settings.
        active: Whether the user is currently active.
    """

    account_id: str
    display_name: str
    email: str
    active: bool


def get_myself(client: JiraCloudClient) -> User:
    """Return the identity of the authenticated caller.

    Used as the connection test in CLI/GUI. For a Service Account token,
    this returns the Service Account's own ``displayName``.

    TODO: implement via ``client.request("GET", "/rest/api/3/myself")``.
    """
    raise NotImplementedError("Implement get_myself — see CLAUDE.md §7 step 4")


def search_users(client: JiraCloudClient, query: str, max_results: int = 50) -> list[User]:
    """Search Jira users by email or display name.

    Args:
        client: Authenticated client.
        query: Free-form text — usually email or display name fragment.
        max_results: Server-side result cap (Atlassian limits this to ~50).

    Returns:
        List of matching :class:`User` instances. Empty list on no matches.

    TODO: implement via ``client.request("GET", "/rest/api/3/user/search", params={...})``.
    Map JSON to User dataclass; default ``email`` to empty string when absent.
    """
    raise NotImplementedError("Implement search_users — see CLAUDE.md §7 step 4")
