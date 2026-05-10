"""HTTP client for Jira Cloud REST API.

The :class:`JiraCloudClient` composes an :class:`~jwe.api.auth.AuthStrategy`
with a :class:`~jwe.api.url_builder.URLBuilder` to issue authenticated
requests against the right endpoint. It is the **only** place in the package
that touches ``requests`` directly; higher-level wrappers
(:mod:`~jwe.api.search`, :mod:`~jwe.api.worklog`, :mod:`~jwe.api.user`)
delegate here.

The client configures retry-with-backoff on transient failures (HTTP 429,
500, 502, 503, 504) and respects ``Retry-After`` headers per RFC 6585.

TODO (claude code, in this order):
1. Implement :meth:`JiraCloudClient.connect` — call ``GET /rest/api/3/myself``
   and return the parsed identity. Wire it into the CLI/GUI connection test.
2. Implement :meth:`JiraCloudClient.request` — generic JSON request method
   used by all higher-level wrappers. Handle 429 with ``Retry-After``,
   transient 5xx with backoff, and produce well-typed errors for 401/403/404.
3. Add structured exception types for auth-vs-permission-vs-not-found so
   the CLI's exit code mapping (PRD §11) works cleanly.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from jwe.api.auth import AuthStrategy
from jwe.api.url_builder import URLBuilder

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT_SECONDS = 30
DEFAULT_USER_AGENT = "jwe/0.1.0 (+https://github.com/elementfortyseven/jira-worklog-exporter)"

# Retry policy: respect Retry-After on 429; back off on common transients.
_RETRY_STATUSES = frozenset({429, 500, 502, 503, 504})
_MAX_RETRIES = 5
_BACKOFF_FACTOR = 1.0  # 1, 2, 4, 8, 16 seconds
_RETRY_METHODS = frozenset({"GET", "POST"})


class JiraApiError(Exception):
    """Base class for all client-side API errors."""


class AuthenticationError(JiraApiError):
    """HTTP 401 — token invalid, expired, or missing scopes for the endpoint.

    In Service Account mode, the most common cause is a token with insufficient
    scopes; the message should suggest checking the scope set rather than
    the token value itself.
    """


class JiraPermissionError(JiraApiError):
    """HTTP 403 — token authenticated, but the underlying account/scope lacks
    permission for the resource.

    For Service Accounts this typically means the account is not a member of
    the relevant project's "Users" role.
    """


class NotFoundError(JiraApiError):
    """HTTP 404 — the resource does not exist (or is not visible to the caller)."""


@dataclass
class JiraCloudClient:
    """Authenticated HTTP client for a single Jira Cloud site.

    Construction is normally indirect via :meth:`from_auth`. Once built,
    the client caches the underlying :class:`requests.Session` with a
    pre-configured retry adapter.

    Attributes:
        auth: The configured authentication strategy.
        url_builder: URL constructor matched to the auth mode.
        session: Underlying ``requests.Session``. Use :meth:`request` rather
            than calling the session directly.
        timeout: Default request timeout in seconds.
    """

    auth: AuthStrategy
    url_builder: URLBuilder
    session: requests.Session
    timeout: float = DEFAULT_TIMEOUT_SECONDS

    @classmethod
    def from_auth(cls, auth: AuthStrategy) -> JiraCloudClient:
        """Build a client from an auth strategy, deriving the URL builder."""
        url_builder = URLBuilder.for_auth(auth)
        session = _build_session(auth)
        return cls(auth=auth, url_builder=url_builder, session=session)

    def connect(self) -> dict[str, Any]:
        """Verify auth by calling ``GET /rest/api/3/myself``.

        Returns the parsed JSON identity (``accountId``, ``displayName``,
        possibly ``emailAddress``). Used as a connection test in both CLI
        and GUI.

        TODO: implement using :meth:`request`. Translate 401 → AuthenticationError
        with a Mode-A-aware message that mentions scopes if appropriate.
        """
        raise NotImplementedError("Implement connect() — see CLAUDE.md §7 step 2")

    def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: Any = None,
    ) -> Any:
        """Issue an authenticated JSON request.

        Args:
            method: HTTP method (``GET``, ``POST``, …).
            path: Path beginning with ``/``, e.g. ``/rest/api/3/myself``.
            params: Optional query string parameters.
            json: Optional JSON body for POST/PUT/PATCH.

        Returns:
            The parsed JSON response body.

        Raises:
            AuthenticationError: on HTTP 401.
            JiraPermissionError: on HTTP 403.
            NotFoundError: on HTTP 404.
            JiraApiError: on any other unexpected error.

        TODO: implement. Map status codes to the typed exceptions above.
        Log the URL but never the auth header or body.
        """
        raise NotImplementedError("Implement request() — see CLAUDE.md §7 step 2")

    def close(self) -> None:
        """Release underlying connections."""
        self.session.close()

    def __enter__(self) -> JiraCloudClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()


def _build_session(auth: AuthStrategy) -> requests.Session:
    """Construct a ``requests.Session`` with retry adapter and default headers.

    Notes:
        * The Authorization header is set on the session, not per-request,
          so it lives in only one place.
        * ``allow_redirects`` is intentionally not constrained here; we set it
          per-request in :meth:`request` (defense against open-redirect
          vectors on the gateway).
    """
    session = requests.Session()

    retry = Retry(
        total=_MAX_RETRIES,
        backoff_factor=_BACKOFF_FACTOR,
        status_forcelist=list(_RETRY_STATUSES),
        allowed_methods=list(_RETRY_METHODS),
        respect_retry_after_header=True,
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)

    session.headers.update(
        {
            "Authorization": auth.authorization_header(),
            "Accept": "application/json",
            "User-Agent": DEFAULT_USER_AGENT,
        }
    )
    return session
