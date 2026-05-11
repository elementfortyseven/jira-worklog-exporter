"""Wrapper for the Jira Cloud user-search and identity endpoints."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

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
    """Return the identity of the authenticated caller."""
    data: dict[str, Any] = client.request("GET", "/rest/api/3/myself")
    return User(
        account_id=data["accountId"],
        display_name=data.get("displayName", ""),
        email=data.get("emailAddress", ""),
        active=True,  # /myself does not include the active field
    )


def search_users(client: JiraCloudClient, query: str, max_results: int = 50) -> list[User]:
    """Search Jira users by email or display name fragment.

    Args:
        client: Authenticated client.
        query: Free-form text — usually email or display name fragment.
        max_results: Server-side result cap (Atlassian limits this to ~50).

    Returns:
        Matching users with accountType ``atlassian`` only.
        App (Connect bots) and customer (JSM portal) accounts are excluded.
    """
    data: list[dict[str, Any]] = client.request(
        "GET",
        "/rest/api/3/user/search",
        params={"query": query, "maxResults": max_results},
    )
    return [
        User(
            account_id=item["accountId"],
            display_name=item.get("displayName", ""),
            email=item.get("emailAddress", ""),
            active=bool(item.get("active", True)),
        )
        for item in data
        if item.get("accountType") == "atlassian"
    ]
