"""Tests for jwe.api.client.

The session construction and auth-header wiring are testable now; the
``connect()`` and ``request()`` methods are stubbed and will get integration
tests using ``responses`` once implemented.
"""

from __future__ import annotations

from jwe.api.auth import ServiceAccountAuth, UserTokenAuth
from jwe.api.client import JiraCloudClient


class TestJiraCloudClientConstruction:
    def test_from_service_account_auth_uses_gateway(
        self, service_account_auth: ServiceAccountAuth
    ) -> None:
        with JiraCloudClient.from_auth(service_account_auth) as client:
            assert client.url_builder.base_url == (
                "https://api.atlassian.com/ex/jira/1a11d016-8984-4c3e-b9ab-142dd06acb1b"
            )

    def test_from_user_token_auth_uses_site_url(
        self, user_token_auth: UserTokenAuth
    ) -> None:
        with JiraCloudClient.from_auth(user_token_auth) as client:
            assert client.url_builder.base_url == "https://acme.atlassian.net"

    def test_session_has_authorization_header(
        self, service_account_auth: ServiceAccountAuth
    ) -> None:
        with JiraCloudClient.from_auth(service_account_auth) as client:
            auth_header = client.session.headers.get("Authorization")
            assert auth_header is not None
            assert auth_header.startswith("Basic ")

    def test_session_user_agent_set(
        self, service_account_auth: ServiceAccountAuth
    ) -> None:
        with JiraCloudClient.from_auth(service_account_auth) as client:
            ua = client.session.headers.get("User-Agent")
            assert ua is not None
            assert ua.startswith("jwe/")


# TODO (claude code): integration tests for connect() and request() once
# those methods are implemented. Use the ``responses`` library to mock
# /rest/api/3/myself and various 401/403/404/429/500 scenarios. See
# CLAUDE.md §10 for known traps to cover in tests.
