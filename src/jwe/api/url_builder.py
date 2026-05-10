"""Base-URL construction for Jira Cloud REST calls.

Atlassian Cloud routes scoped tokens through the **Platform API Gateway** at
``https://api.atlassian.com/ex/jira/{cloudId}/...``, while legacy personal
tokens use the **site URL** ``https://<tenant>.atlassian.net/...``. Service
Account tokens are always scoped, so they always go through the gateway.

Mixing these up produces silent 401s with no useful diagnostic, which is why
this module exists as a single source of truth. Every API call must pass
through :func:`URLBuilder.build` — never construct URLs ad hoc.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from jwe.api.auth import AuthStrategy, ServiceAccountAuth, UserTokenAuth

_CLOUD_ID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
_SITE_URL_RE = re.compile(r"^https://[a-z0-9][a-z0-9-]*\.atlassian\.net$", re.IGNORECASE)


def validate_cloud_id(cloud_id: str) -> None:
    """Validate that ``cloud_id`` looks like an Atlassian site UUID.

    Raises:
        ValueError: if the cloud_id does not match the expected UUID format.
    """
    if not _CLOUD_ID_RE.match(cloud_id):
        raise ValueError(
            f"Invalid cloud_id {cloud_id!r}. Expected a UUID like "
            "'1a11d016-8984-4c3e-b9ab-142dd06acb1b'."
        )


def validate_site_url(site_url: str) -> None:
    """Validate that ``site_url`` is a well-formed Atlassian site URL.

    Raises:
        ValueError: if the URL is not of the form
            ``https://<tenant>.atlassian.net`` (no trailing slash, no path).
    """
    if not _SITE_URL_RE.match(site_url):
        raise ValueError(
            f"Invalid site_url {site_url!r}. Expected something like "
            "'https://acme.atlassian.net' (no trailing slash, no path)."
        )


@dataclass(frozen=True)
class URLBuilder:
    """Builds fully-qualified REST URLs for the configured auth mode.

    Construction is normally indirect via :meth:`for_auth`, which inspects an
    :class:`~jwe.api.auth.AuthStrategy` and picks the correct base URL.

    The builder is auth-mode aware but auth-credential agnostic: it never
    sees tokens or emails.

    Example:
        >>> auth = ServiceAccountAuth(
        ...     email="bot@serviceaccount.atlassian.com",
        ...     token="abc123",
        ...     cloud_id="1a11d016-8984-4c3e-b9ab-142dd06acb1b",
        ... )
        >>> ub = URLBuilder.for_auth(auth)
        >>> ub.build("/rest/api/3/myself")
        'https://api.atlassian.com/ex/jira/1a11d016-8984-4c3e-b9ab-142dd06acb1b/rest/api/3/myself'
    """

    base_url: str
    """Fully-qualified base URL with no trailing slash."""

    @classmethod
    def for_auth(cls, auth: AuthStrategy) -> URLBuilder:
        """Construct the appropriate URLBuilder for the given auth strategy.

        Raises:
            TypeError: if ``auth`` is not a known concrete strategy.
            ValueError: if the auth strategy carries an invalid cloud_id
                or site_url.
        """
        if isinstance(auth, ServiceAccountAuth):
            validate_cloud_id(auth.cloud_id)
            return cls(base_url=f"https://api.atlassian.com/ex/jira/{auth.cloud_id}")

        if isinstance(auth, UserTokenAuth):
            validate_site_url(auth.site_url)
            return cls(base_url=auth.site_url)

        raise TypeError(f"Unknown AuthStrategy subclass: {type(auth).__name__}")

    def build(self, path: str) -> str:
        """Join a REST path onto the base URL.

        ``path`` should start with a leading slash (e.g. ``/rest/api/3/myself``).
        Trailing slashes on the base URL are stripped if present.

        Raises:
            ValueError: if ``path`` is empty or doesn't start with ``/``.
        """
        if not path:
            raise ValueError("path must not be empty")
        if not path.startswith("/"):
            raise ValueError(f"path must start with '/', got {path!r}")
        return f"{self.base_url.rstrip('/')}{path}"
