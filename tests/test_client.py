"""Tests for jwe.api.client.

Design note on retry coverage
------------------------------
The session adapter uses ``urllib3.util.retry.Retry`` for backoff on 429 and
5xx responses.  The ``responses`` library patches ``HTTPAdapter.send``, which
means urllib3 never runs during tests and the adapter's retry loop cannot be
exercised with ``responses`` mocks.

We therefore split retry coverage into two honest layers:

1. **Adapter configuration** — unit-test that the ``Retry`` object carries the
   right ``status_forcelist`` and ``respect_retry_after_header=True``.  This
   proves the policy is wired up correctly for production.

2. **Exhausted-retry path** — use ``responses`` to hand ``request()`` a final
   429 or 500 (as urllib3 would after exhausting retries) and assert the
   correct ``JiraApiError`` is raised.

What we deliberately do *not* test here is "429 → urllib3 retries internally →
200", because that path belongs to urllib3's own test suite, not ours.
"""

from __future__ import annotations

import logging

import pytest
import requests
import responses
from requests.adapters import HTTPAdapter

from jwe.api.auth import ServiceAccountAuth, UserTokenAuth
from jwe.api.client import (
    _MAX_RETRIES,
    _RETRY_STATUSES,
    AuthenticationError,
    JiraApiError,
    JiraCloudClient,
    JiraPermissionError,
    NotFoundError,
)

# ---------------------------------------------------------------------------
# Shared fixture data
# ---------------------------------------------------------------------------

_MYSELF: dict[str, object] = {
    "accountId": "5b10ac8d82e05b22cc7d4ef5",
    "displayName": "Jira Bot",
    "emailAddress": "jwe-bot@serviceaccount.atlassian.com",
    "active": True,
}

_CLOUD_ID = "1a11d016-8984-4c3e-b9ab-142dd06acb1b"
_SA_BASE = f"https://api.atlassian.com/ex/jira/{_CLOUD_ID}"
_SA_MYSELF = f"{_SA_BASE}/rest/api/3/myself"
_UT_MYSELF = "https://acme.atlassian.net/rest/api/3/myself"


# ---------------------------------------------------------------------------
# Construction (pre-existing tests, kept verbatim)
# ---------------------------------------------------------------------------


class TestJiraCloudClientConstruction:
    def test_from_service_account_auth_uses_gateway(
        self, service_account_auth: ServiceAccountAuth
    ) -> None:
        with JiraCloudClient.from_auth(service_account_auth) as client:
            assert client.url_builder.base_url == _SA_BASE

    def test_from_user_token_auth_uses_site_url(self, user_token_auth: UserTokenAuth) -> None:
        with JiraCloudClient.from_auth(user_token_auth) as client:
            assert client.url_builder.base_url == "https://acme.atlassian.net"

    def test_session_has_authorization_header(
        self, service_account_auth: ServiceAccountAuth
    ) -> None:
        with JiraCloudClient.from_auth(service_account_auth) as client:
            auth_header = client.session.headers.get("Authorization")
            assert auth_header is not None
            assert auth_header.startswith("Basic ")

    def test_session_user_agent_set(self, service_account_auth: ServiceAccountAuth) -> None:
        with JiraCloudClient.from_auth(service_account_auth) as client:
            ua = client.session.headers.get("User-Agent")
            assert ua is not None
            assert ua.startswith("jwe/")


# ---------------------------------------------------------------------------
# Retry adapter configuration
# ---------------------------------------------------------------------------


class TestSessionRetryConfiguration:
    """Verify the urllib3 Retry policy wired into the session adapter."""

    def test_retries_on_429(self, service_account_auth: ServiceAccountAuth) -> None:
        assert 429 in _RETRY_STATUSES

    def test_retries_on_5xx(self, service_account_auth: ServiceAccountAuth) -> None:
        assert {500, 502, 503, 504}.issubset(_RETRY_STATUSES)

    def test_respects_retry_after_header(self, service_account_auth: ServiceAccountAuth) -> None:
        with JiraCloudClient.from_auth(service_account_auth) as client:
            adapter: HTTPAdapter = client.session.get_adapter("https://")  # type: ignore[assignment]
            assert adapter.max_retries.respect_retry_after_header is True  # type: ignore[union-attr]

    def test_max_retries_value(self, service_account_auth: ServiceAccountAuth) -> None:
        with JiraCloudClient.from_auth(service_account_auth) as client:
            adapter: HTTPAdapter = client.session.get_adapter("https://")  # type: ignore[assignment]
            assert adapter.max_retries.total == _MAX_RETRIES  # type: ignore[union-attr]


# ---------------------------------------------------------------------------
# connect()
# ---------------------------------------------------------------------------


class TestConnect:
    @responses.activate
    def test_service_account_calls_gateway_url(
        self, service_account_auth: ServiceAccountAuth
    ) -> None:
        responses.add(responses.GET, _SA_MYSELF, json=_MYSELF, status=200)
        with JiraCloudClient.from_auth(service_account_auth) as client:
            result = client.connect()
        assert result["accountId"] == _MYSELF["accountId"]
        assert result["displayName"] == _MYSELF["displayName"]

    @responses.activate
    def test_user_token_calls_site_url(self, user_token_auth: UserTokenAuth) -> None:
        responses.add(responses.GET, _UT_MYSELF, json=_MYSELF, status=200)
        with JiraCloudClient.from_auth(user_token_auth) as client:
            result = client.connect()
        assert result["accountId"] == _MYSELF["accountId"]

    @responses.activate
    def test_connect_logs_identity_label_and_display_name(
        self, service_account_auth: ServiceAccountAuth, caplog: pytest.LogCaptureFixture
    ) -> None:
        responses.add(responses.GET, _SA_MYSELF, json=_MYSELF, status=200)
        with (
            JiraCloudClient.from_auth(service_account_auth) as client,
            caplog.at_level(logging.INFO, logger="jwe.api.client"),
        ):
            client.connect()
        assert "Jira Bot" in caplog.text
        assert "service-account" in caplog.text


# ---------------------------------------------------------------------------
# request() — status-code mapping
# ---------------------------------------------------------------------------


class TestRequestStatusMapping:
    @responses.activate
    def test_200_returns_json(self, service_account_auth: ServiceAccountAuth) -> None:
        responses.add(responses.GET, _SA_MYSELF, json=_MYSELF, status=200)
        with JiraCloudClient.from_auth(service_account_auth) as client:
            result = client.request("GET", "/rest/api/3/myself")
        assert result == _MYSELF

    @responses.activate
    def test_401_service_account_raises_with_scope_hint(
        self, service_account_auth: ServiceAccountAuth
    ) -> None:
        responses.add(responses.GET, _SA_MYSELF, status=401)
        with (
            JiraCloudClient.from_auth(service_account_auth) as client,
            pytest.raises(AuthenticationError, match="scope"),
        ):
            client.request("GET", "/rest/api/3/myself")

    @responses.activate
    def test_401_user_token_raises_without_scope_hint(self, user_token_auth: UserTokenAuth) -> None:
        responses.add(responses.GET, _UT_MYSELF, status=401)
        with (
            JiraCloudClient.from_auth(user_token_auth) as client,
            pytest.raises(AuthenticationError) as exc_info,
        ):
            client.request("GET", "/rest/api/3/myself")
        assert "scope" not in str(exc_info.value).lower()

    @responses.activate
    def test_403_raises_permission_error(self, service_account_auth: ServiceAccountAuth) -> None:
        responses.add(responses.GET, _SA_MYSELF, status=403)
        with (
            JiraCloudClient.from_auth(service_account_auth) as client,
            pytest.raises(JiraPermissionError),
        ):
            client.request("GET", "/rest/api/3/myself")

    @responses.activate
    def test_404_raises_not_found(self, service_account_auth: ServiceAccountAuth) -> None:
        responses.add(responses.GET, _SA_MYSELF, status=404)
        with (
            JiraCloudClient.from_auth(service_account_auth) as client,
            pytest.raises(NotFoundError),
        ):
            client.request("GET", "/rest/api/3/myself")

    @responses.activate
    def test_429_exhausted_raises_api_error(self, service_account_auth: ServiceAccountAuth) -> None:
        # Simulates what request() receives after urllib3 has exhausted its retries.
        responses.add(responses.GET, _SA_MYSELF, status=429)
        with (
            JiraCloudClient.from_auth(service_account_auth) as client,
            pytest.raises(JiraApiError),
        ):
            client.request("GET", "/rest/api/3/myself")

    @responses.activate
    def test_500_exhausted_raises_api_error(self, service_account_auth: ServiceAccountAuth) -> None:
        # Simulates what request() receives after urllib3 has exhausted its retries.
        responses.add(responses.GET, _SA_MYSELF, status=500)
        with (
            JiraCloudClient.from_auth(service_account_auth) as client,
            pytest.raises(JiraApiError),
        ):
            client.request("GET", "/rest/api/3/myself")

    @responses.activate
    def test_unexpected_non_2xx_raises_api_error(
        self, service_account_auth: ServiceAccountAuth
    ) -> None:
        responses.add(responses.GET, _SA_MYSELF, status=418)
        with (
            JiraCloudClient.from_auth(service_account_auth) as client,
            pytest.raises(JiraApiError),
        ):
            client.request("GET", "/rest/api/3/myself")

    @responses.activate
    def test_200_with_non_json_body_raises_api_error(
        self, service_account_auth: ServiceAccountAuth
    ) -> None:
        responses.add(
            responses.GET, _SA_MYSELF, body="<html>error</html>",
            content_type="text/html", status=200,
        )
        with (
            JiraCloudClient.from_auth(service_account_auth) as client,
            pytest.raises(JiraApiError, match="non-JSON"),
        ):
            client.request("GET", "/rest/api/3/myself")

    @responses.activate
    def test_connection_error_raises_api_error(
        self, service_account_auth: ServiceAccountAuth
    ) -> None:
        responses.add(responses.GET, _SA_MYSELF, body=requests.ConnectionError("DNS failure"))
        with (
            JiraCloudClient.from_auth(service_account_auth) as client,
            pytest.raises(JiraApiError, match="Network error"),
        ):
            client.request("GET", "/rest/api/3/myself")


# ---------------------------------------------------------------------------
# Security: token must not appear in exceptions or logs
# ---------------------------------------------------------------------------


class TestTokenNeverLeaks:
    @responses.activate
    def test_token_absent_from_401_exception_service_account(
        self, service_account_auth: ServiceAccountAuth
    ) -> None:
        responses.add(responses.GET, _SA_MYSELF, status=401)
        with (
            JiraCloudClient.from_auth(service_account_auth) as client,
            pytest.raises(AuthenticationError) as exc_info,
        ):
            client.request("GET", "/rest/api/3/myself")
        assert service_account_auth.token not in str(exc_info.value)

    @responses.activate
    def test_token_absent_from_401_exception_user_token(
        self, user_token_auth: UserTokenAuth
    ) -> None:
        responses.add(responses.GET, _UT_MYSELF, status=401)
        with (
            JiraCloudClient.from_auth(user_token_auth) as client,
            pytest.raises(AuthenticationError) as exc_info,
        ):
            client.request("GET", "/rest/api/3/myself")
        assert user_token_auth.token not in str(exc_info.value)

    @responses.activate
    def test_token_absent_from_debug_logs_on_success(
        self,
        service_account_auth: ServiceAccountAuth,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        responses.add(responses.GET, _SA_MYSELF, json=_MYSELF, status=200)
        with (
            JiraCloudClient.from_auth(service_account_auth) as client,
            caplog.at_level(logging.DEBUG, logger="jwe.api.client"),
        ):
            client.connect()
        all_messages = " ".join(r.message for r in caplog.records)
        assert service_account_auth.token not in all_messages
