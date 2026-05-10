"""Authentication strategies for Jira Cloud.

Two modes are supported:

* **Service Account** (preferred): scoped API tokens issued by an Atlassian
  Organisation Admin via ``admin.atlassian.com``. Tokens carry explicit scopes
  and authenticate via either Basic or Bearer auth against the Platform
  Gateway URL ``api.atlassian.com/ex/jira/{cloudId}``.

* **Personal Token** (fallback): legacy or scoped API tokens issued by
  individual users at ``id.atlassian.com``. Authenticate via Basic auth
  against the site URL ``<tenant>.atlassian.net``.

The chosen mode determines both the ``Authorization`` header and the base
URL — see :mod:`jwe.api.url_builder` for the URL side. ``AuthStrategy``
encapsulates only the header construction and identity metadata; it must
never know about URLs.

Tokens are masked in ``repr()`` so they cannot leak via logs or stack traces.
"""

from __future__ import annotations

import base64
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import StrEnum


class AuthMode(StrEnum):
    """Identifies which authentication regime is in use."""

    SERVICE_ACCOUNT = "service-account"
    USER_TOKEN = "user-token"


class AuthHeaderStyle(StrEnum):
    """How to format the Authorization header."""

    BASIC = "basic"
    BEARER = "bearer"


def _mask_token(token: str) -> str:
    """Return a token representation safe for logs.

    Shows the first 4 and last 4 characters; everything in between is
    replaced with ``…``. Tokens shorter than 12 characters are fully masked.
    """
    if len(token) < 12:
        return "***"
    return f"{token[:4]}…{token[-4:]}"


class AuthStrategy(ABC):
    """Abstract base for authentication strategies.

    Concrete subclasses produce the ``Authorization`` header value and
    expose enough identity metadata for logging and connection-test feedback.
    """

    mode: AuthMode

    @abstractmethod
    def authorization_header(self) -> str:
        """Return the value for the ``Authorization`` HTTP header."""

    @abstractmethod
    def identity_label(self) -> str:
        """Return a human-readable label for logs and UI status messages."""


@dataclass(frozen=True)
class ServiceAccountAuth(AuthStrategy):
    """Authentication for an Atlassian Service Account.

    The Service Account email is typically ``<id>@serviceaccount.atlassian.com``.
    The token is created via ``admin.atlassian.com → Directory → Service
    accounts → Create credential → API token`` and **must** carry scopes
    appropriate for the operations the tool performs (read-only for this
    project — see ``CLAUDE.md`` §3).

    Attributes:
        email: Service Account email address.
        token: API token value. Never logged in plain text.
        header_style: Either Basic (default) or Bearer auth.
        cloud_id: Site UUID. Stored here for convenience even though
            URL construction lives in :mod:`url_builder`; both consumers
            need it.
    """

    email: str
    token: str = field(repr=False)
    cloud_id: str
    header_style: AuthHeaderStyle = AuthHeaderStyle.BASIC

    mode: AuthMode = field(default=AuthMode.SERVICE_ACCOUNT, init=False)

    def authorization_header(self) -> str:
        """Construct the Authorization header per the configured style."""
        if self.header_style is AuthHeaderStyle.BEARER:
            return f"Bearer {self.token}"
        # Basic: base64("email:token")
        raw = f"{self.email}:{self.token}".encode()
        return f"Basic {base64.b64encode(raw).decode('ascii')}"

    def identity_label(self) -> str:
        """Return a label like ``service-account:bot@…atlassian.com``."""
        return f"service-account:{self.email}"

    def __repr__(self) -> str:
        return (
            f"ServiceAccountAuth(email={self.email!r}, "
            f"token={_mask_token(self.token)!r}, "
            f"cloud_id={self.cloud_id!r}, "
            f"header_style={self.header_style.value!r})"
        )


@dataclass(frozen=True)
class UserTokenAuth(AuthStrategy):
    """Authentication for a personal Atlassian account.

    The email is the user's Atlassian login. The token is created at
    ``id.atlassian.com/manage-profile/security/api-tokens``. Tokens may be
    classic (no scopes) or scoped; both are accepted here, but classic tokens
    need the legacy site URL (``<tenant>.atlassian.net``) — see
    :mod:`url_builder`.

    Attributes:
        email: Atlassian account email.
        token: API token value. Never logged in plain text.
        site_url: Site base URL, e.g. ``https://acme.atlassian.net``.
            Stored here for convenience; URL construction lives in
            :mod:`url_builder`.
    """

    email: str
    token: str = field(repr=False)
    site_url: str

    mode: AuthMode = field(default=AuthMode.USER_TOKEN, init=False)

    def authorization_header(self) -> str:
        """Construct the Basic Authorization header."""
        raw = f"{self.email}:{self.token}".encode()
        return f"Basic {base64.b64encode(raw).decode('ascii')}"

    def identity_label(self) -> str:
        """Return a label like ``user-token:user@example.com``."""
        return f"user-token:{self.email}"

    def __repr__(self) -> str:
        return (
            f"UserTokenAuth(email={self.email!r}, "
            f"token={_mask_token(self.token)!r}, "
            f"site_url={self.site_url!r})"
        )
