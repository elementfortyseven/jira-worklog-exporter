"""Service layer — shared use-cases for CLI and GUI frontends.

Both frontends are pure view layers: they collect user input and render
output. All domain logic lives here, fully typed and independently
testable. This module knows nothing about argparse, Tk widgets, threads,
or UI strings — those are view concerns.

Key-schema for token persistence: ``jwe:{auth_mode}:{identifier}``
where *identifier* is the cloud_id (Service Account) or site_url
(User Token).
"""

from __future__ import annotations

import logging
import os
import threading
import types
from collections.abc import Iterator

try:
    import keyring as _keyring_module
except ImportError:
    _keyring_module = None  # type: ignore[assignment]

from jwe.api.auth import AuthMode
from jwe.api.client import AuthenticationError, JiraApiError, JiraCloudClient, JiraPermissionError
from jwe.api.tenant_info import TenantInfo
from jwe.api.tenant_info import discover_cloud_id as _discover_cloud_id
from jwe.api.user import User
from jwe.api.user import search_users as _search_users
from jwe.config import ExportConfig
from jwe.exporter import ExportProgress, ExportResult
from jwe.exporter import run_export as _run_export

logger = logging.getLogger(__name__)

# Module-level reference so tests can monkeypatch via mock.patch.object(service, "keyring", ...).
keyring: types.ModuleType | None = _keyring_module

__all__ = [
    "AuthenticationError",
    "ExportProgress",
    "ExportResult",
    "JiraApiError",
    "JiraPermissionError",
    "config_from_env",
    "delete_token",
    "discover_cloud_id",
    "load_token",
    "run_export",
    "save_token",
    "search_users",
    "test_connection",
]

_KEYRING_SERVICE = "jwe"


# ---------------------------------------------------------------------------
# Connection / authentication
# ---------------------------------------------------------------------------


def test_connection(config: ExportConfig) -> User:
    """Verify connectivity and return the authenticated identity.

    Args:
        config: Validated export configuration.

    Returns:
        The :class:`~jwe.api.user.User` identity of the authenticated
        caller (the service account itself in Mode A).

    Raises:
        AuthenticationError: HTTP 401 — token invalid, expired, or missing
            scopes.
        JiraPermissionError: HTTP 403 — authenticated but lacks permission.
        JiraApiError: Any other API error.
    """
    auth = config.build_auth()
    with JiraCloudClient.from_auth(auth) as client:
        identity = client.connect()
    return User(
        account_id=identity["accountId"],
        display_name=identity.get("displayName", ""),
        email=identity.get("emailAddress", ""),
        active=True,
    )


def search_users(
    config: ExportConfig,
    query: str,
    max_results: int = 50,
) -> list[User]:
    """Search Jira users matching a query string.

    Args:
        config: Validated export configuration supplying auth and endpoint.
        query: Free-form text — email or display name fragment.
        max_results: Server-side result cap (Atlassian limits to ~50).

    Returns:
        Matching :class:`~jwe.api.user.User` objects (``atlassian`` account
        type only; app and customer accounts are excluded).

    Raises:
        AuthenticationError: HTTP 401.
        JiraPermissionError: HTTP 403.
        JiraApiError: Any other API error.
    """
    auth = config.build_auth()
    with JiraCloudClient.from_auth(auth) as client:
        return _search_users(client, query, max_results)


# ---------------------------------------------------------------------------
# Cloud ID discovery
# ---------------------------------------------------------------------------


def discover_cloud_id(site_url: str) -> TenantInfo:
    """Discover the cloud ID for a Jira Cloud site via ``/_edge/tenant_info``.

    Args:
        site_url: Site base URL, e.g. ``https://acme.atlassian.net``
            (no trailing slash, no path).

    Returns:
        A :class:`~jwe.api.tenant_info.TenantInfo` with the cloud ID.

    Raises:
        ValueError: If ``site_url`` is malformed.
        TenantInfoError: If the endpoint is unreachable or returns unexpected
            data.
    """
    return _discover_cloud_id(site_url)


# ---------------------------------------------------------------------------
# Export orchestration
# ---------------------------------------------------------------------------


def run_export(
    config: ExportConfig,
    cancel_event: threading.Event | None = None,
) -> Iterator[ExportProgress | ExportResult]:
    """Run an export, delegating to :func:`jwe.exporter.run_export`.

    Both CLI and GUI import only from :mod:`jwe.service`, so neither
    depends on :mod:`jwe.exporter` directly.

    Args:
        config: Validated export configuration.
        cancel_event: Optional cancellation flag. When set, the run stops
            cleanly between issues.

    Yields:
        Zero or more :class:`~jwe.exporter.ExportProgress` events followed
        by exactly one :class:`~jwe.exporter.ExportResult`.
    """
    yield from _run_export(config, cancel_event)


# ---------------------------------------------------------------------------
# Token persistence (keyring)
# ---------------------------------------------------------------------------


def _keyring_key(auth_mode: AuthMode, identifier: str) -> str:
    return f"jwe:{auth_mode}:{identifier}"


def _require_keyring() -> None:
    if keyring is None:
        raise RuntimeError(
            "Token persistence requires 'keyring' — install with: pip install jwe[keyring]"
        )


def save_token(auth_mode: AuthMode, identifier: str, token: str) -> None:
    """Persist an API token in the OS credential store.

    Args:
        auth_mode: :attr:`~jwe.api.auth.AuthMode.SERVICE_ACCOUNT` or
            :attr:`~jwe.api.auth.AuthMode.USER_TOKEN`.
        identifier: ``cloud_id`` for Service Account mode; ``site_url`` for
            User Token mode. Forms the keyring key together with
            ``auth_mode``.
        token: Plaintext API token value.

    Raises:
        RuntimeError: If ``keyring`` is not installed.
    """
    _require_keyring()
    assert keyring is not None
    keyring.set_password(_KEYRING_SERVICE, _keyring_key(auth_mode, identifier), token)


def load_token(auth_mode: AuthMode, identifier: str) -> str | None:
    """Load an API token from the OS credential store.

    Args:
        auth_mode: Auth mode used when the token was saved.
        identifier: ``cloud_id`` or ``site_url`` (must match
            :func:`save_token`).

    Returns:
        The token string, or ``None`` if not found.

    Raises:
        RuntimeError: If ``keyring`` is not installed.
    """
    _require_keyring()
    assert keyring is not None
    try:
        return keyring.get_password(  # type: ignore[no-any-return]
            _KEYRING_SERVICE, _keyring_key(auth_mode, identifier)
        )
    except Exception as exc:  # keyring backends raise OS-specific types we cannot enumerate
        logger.debug("Keyring read failed: %r", exc)
        return None


def delete_token(auth_mode: AuthMode, identifier: str) -> None:
    """Remove an API token from the OS credential store.

    Deleting a token that is not present is a no-op (idempotent): backends
    such as the Windows credential store raise on a missing entry, which we
    treat as success -- consistent with :func:`load_token`'s tolerant read.

    Args:
        auth_mode: Auth mode used when the token was saved.
        identifier: ``cloud_id`` or ``site_url`` (must match
            :func:`save_token`).

    Raises:
        RuntimeError: If ``keyring`` is not installed.
    """
    _require_keyring()
    assert keyring is not None
    try:
        keyring.delete_password(_KEYRING_SERVICE, _keyring_key(auth_mode, identifier))
    except Exception as exc:  # keyring backends raise OS-specific types; a missing token is a no-op
        logger.debug("Keyring delete failed (no-op): %r", exc)


# ---------------------------------------------------------------------------
# Config from environment (FR-08)
# ---------------------------------------------------------------------------


def config_from_env() -> ExportConfig:
    """Build an :class:`~jwe.config.ExportConfig` from JWE_* env vars (FR-08).

    Reads the following variables:

    * ``JWE_AUTH_MODE`` — ``service-account`` or ``user-token``
      (default: ``service-account``)
    * ``JWE_CLOUD_ID`` — cloud ID (Service Account mode)
    * ``JWE_SITE_URL`` — site URL (User Token mode)
    * ``JWE_EMAIL`` — email address for the active mode
    * ``JWE_API_TOKEN`` — API token (both modes)

    ``JWE_EMAIL`` maps to both
    :attr:`~jwe.config.ExportConfig.service_account_email` and
    :attr:`~jwe.config.ExportConfig.email` so the caller does not need to
    know the mode before reading the env set.

    Returns:
        A partially-filled :class:`~jwe.config.ExportConfig`. The caller
        must invoke :meth:`~jwe.config.ExportConfig.validate` before use,
        because partial or empty env sets are accepted here.
    """
    raw_mode = os.environ.get("JWE_AUTH_MODE", AuthMode.SERVICE_ACCOUNT.value)
    try:
        auth_mode = AuthMode(raw_mode)
    except ValueError:
        auth_mode = AuthMode.SERVICE_ACCOUNT

    email_value = os.environ.get("JWE_EMAIL", "")

    return ExportConfig(
        auth_mode=auth_mode,
        cloud_id=os.environ.get("JWE_CLOUD_ID", ""),
        service_account_email=email_value,
        site_url=os.environ.get("JWE_SITE_URL", ""),
        email=email_value,
        api_token=os.environ.get("JWE_API_TOKEN", ""),
    )
