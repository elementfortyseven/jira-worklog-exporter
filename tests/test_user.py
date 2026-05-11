"""Tests for jwe.api.user."""

from __future__ import annotations

from urllib.parse import parse_qs, urlparse

import responses

from jwe.api.auth import ServiceAccountAuth
from jwe.api.client import JiraCloudClient
from jwe.api.user import User, get_myself, search_users

_CLOUD_ID = "1a11d016-8984-4c3e-b9ab-142dd06acb1b"
_SA_BASE = f"https://api.atlassian.com/ex/jira/{_CLOUD_ID}"
_SA_MYSELF = f"{_SA_BASE}/rest/api/3/myself"
_SA_USER_SEARCH = f"{_SA_BASE}/rest/api/3/user/search"

_MYSELF_RESPONSE: dict[str, object] = {
    "accountId": "5b10ac8d82e05b22cc7d4ef5",
    "accountType": "atlassian",
    "displayName": "Jira Bot",
    "emailAddress": "jwe-bot@serviceaccount.atlassian.com",
}

_USER_A: dict[str, object] = {
    "accountId": "aaa111",
    "accountType": "atlassian",
    "displayName": "Tanja Beispiel",
    "emailAddress": "tanja@example.com",
    "active": True,
}
_USER_B: dict[str, object] = {
    "accountId": "bbb222",
    "accountType": "atlassian",
    "displayName": "Klaus Muster",
    "emailAddress": "klaus@example.com",
    "active": True,
}
_USER_C: dict[str, object] = {
    "accountId": "ccc333",
    "accountType": "atlassian",
    "displayName": "Erika Schmidt",
    "emailAddress": "erika@example.com",
    "active": False,
}
_USER_APP: dict[str, object] = {
    "accountId": "bot000",
    "accountType": "app",
    "displayName": "Connect Bot",
    "emailAddress": "",
    "active": True,
}
_USER_CUSTOMER: dict[str, object] = {
    "accountId": "cust999",
    "accountType": "customer",
    "displayName": "Portal User",
    "emailAddress": "portal@customer.com",
    "active": True,
}


# ---------------------------------------------------------------------------
# get_myself
# ---------------------------------------------------------------------------


class TestGetMyself:
    @responses.activate
    def test_complete_response_maps_correctly(
        self, service_account_auth: ServiceAccountAuth
    ) -> None:
        responses.add(responses.GET, _SA_MYSELF, json=_MYSELF_RESPONSE, status=200)
        with JiraCloudClient.from_auth(service_account_auth) as client:
            user = get_myself(client)
        assert user == User(
            account_id="5b10ac8d82e05b22cc7d4ef5",
            display_name="Jira Bot",
            email="jwe-bot@serviceaccount.atlassian.com",
            active=True,
        )

    @responses.activate
    def test_missing_email_defaults_to_empty_string(
        self, service_account_auth: ServiceAccountAuth
    ) -> None:
        payload = {k: v for k, v in _MYSELF_RESPONSE.items() if k != "emailAddress"}
        responses.add(responses.GET, _SA_MYSELF, json=payload, status=200)
        with JiraCloudClient.from_auth(service_account_auth) as client:
            user = get_myself(client)
        assert user.email == ""

    @responses.activate
    def test_active_defaults_to_true(
        self, service_account_auth: ServiceAccountAuth
    ) -> None:
        responses.add(responses.GET, _SA_MYSELF, json=_MYSELF_RESPONSE, status=200)
        with JiraCloudClient.from_auth(service_account_auth) as client:
            user = get_myself(client)
        assert user.active is True


# ---------------------------------------------------------------------------
# search_users
# ---------------------------------------------------------------------------


class TestSearchUsers:
    @responses.activate
    def test_three_atlassian_users_all_returned(
        self, service_account_auth: ServiceAccountAuth
    ) -> None:
        responses.add(
            responses.GET, _SA_USER_SEARCH,
            json=[_USER_A, _USER_B, _USER_C], status=200,
        )
        with JiraCloudClient.from_auth(service_account_auth) as client:
            result = search_users(client, query="example")
        assert len(result) == 3
        assert result[0].account_id == "aaa111"
        assert result[1].account_id == "bbb222"
        assert result[2].account_id == "ccc333"

    @responses.activate
    def test_app_and_customer_accounts_filtered_out(
        self, service_account_auth: ServiceAccountAuth
    ) -> None:
        responses.add(
            responses.GET, _SA_USER_SEARCH,
            json=[_USER_A, _USER_APP, _USER_CUSTOMER, _USER_B], status=200,
        )
        with JiraCloudClient.from_auth(service_account_auth) as client:
            result = search_users(client, query="example")
        assert len(result) == 2
        assert all(u.account_id in {"aaa111", "bbb222"} for u in result)

    @responses.activate
    def test_empty_response_returns_empty_list(
        self, service_account_auth: ServiceAccountAuth
    ) -> None:
        responses.add(responses.GET, _SA_USER_SEARCH, json=[], status=200)
        with JiraCloudClient.from_auth(service_account_auth) as client:
            result = search_users(client, query="nobody")
        assert result == []

    @responses.activate
    def test_query_and_max_results_sent_as_url_params(
        self, service_account_auth: ServiceAccountAuth
    ) -> None:
        responses.add(responses.GET, _SA_USER_SEARCH, json=[_USER_A], status=200)
        with JiraCloudClient.from_auth(service_account_auth) as client:
            search_users(client, query="tanja", max_results=25)
        params = parse_qs(urlparse(responses.calls[0].request.url).query)
        assert params["query"] == ["tanja"]
        assert params["maxResults"] == ["25"]
