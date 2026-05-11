"""Tests for jwe.api.search."""

from __future__ import annotations

import json
from datetime import date

import pytest
import responses

from jwe.api.auth import ServiceAccountAuth
from jwe.api.client import JiraCloudClient
from jwe.api.search import IssueRef, build_jql, iter_issues

_CLOUD_ID = "1a11d016-8984-4c3e-b9ab-142dd06acb1b"
_SA_BASE = f"https://api.atlassian.com/ex/jira/{_CLOUD_ID}"
_SEARCH_URL = f"{_SA_BASE}/rest/api/3/search/jql"

_FROM = date(2026, 4, 1)
_TO = date(2026, 4, 30)

_ISSUE_1 = {"key": "PROJ-1", "fields": {"summary": "Alpha",   "project": {"key": "PROJ", "name": "Project One"}}}
_ISSUE_2 = {"key": "PROJ-2", "fields": {"summary": "Beta",    "project": {"key": "PROJ", "name": "Project One"}}}
_ISSUE_3 = {"key": "SUPP-9", "fields": {"summary": "Gamma",   "project": {"key": "SUPP", "name": "Support"}}}
_ISSUE_4 = {"key": "PROJ-3", "fields": {"summary": "Delta",   "project": {"key": "PROJ", "name": "Project One"}}}
_ISSUE_5 = {"key": "PROJ-4", "fields": {"summary": "Epsilon", "project": {"key": "PROJ", "name": "Project One"}}}


class TestBuildJql:
    def test_with_projects_produces_correct_jql(self) -> None:
        result = build_jql(["aid1", "aid2"], _FROM, _TO, ["PROJ", "SUPP"])
        assert result == (
            'worklogAuthor in ("aid1", "aid2")'
            ' AND worklogDate >= "2026-04-01"'
            ' AND worklogDate <= "2026-04-30"'
            " AND project in (PROJ, SUPP)"
        )

    def test_without_project_keys_omits_project_clause(self) -> None:
        result = build_jql(["aid1"], _FROM, _TO)
        assert "project" not in result
        assert result == (
            'worklogAuthor in ("aid1")'
            ' AND worklogDate >= "2026-04-01"'
            ' AND worklogDate <= "2026-04-30"'
        )

    def test_empty_account_ids_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="account_ids"):
            build_jql([], _FROM, _TO)

    def test_invalid_project_key_lowercase_raises(self) -> None:
        with pytest.raises(ValueError, match="proj"):
            build_jql(["aid1"], _FROM, _TO, ["proj"])

    def test_invalid_project_key_with_hyphen_raises(self) -> None:
        with pytest.raises(ValueError, match="PROJ-1"):
            build_jql(["aid1"], _FROM, _TO, ["PROJ-1"])

    def test_account_id_with_embedded_quote_is_escaped(self) -> None:
        result = build_jql(['abc"def'], _FROM, _TO)
        assert 'worklogAuthor in ("abc\\"def")' in result


class TestIterIssues:
    @responses.activate
    def test_single_page_yields_three_issues(
        self, service_account_auth: ServiceAccountAuth
    ) -> None:
        responses.add(
            responses.POST, _SEARCH_URL,
            json={"issues": [_ISSUE_1, _ISSUE_2, _ISSUE_3]},
            status=200,
        )
        with JiraCloudClient.from_auth(service_account_auth) as client:
            result = list(iter_issues(client, "jql"))
        assert result == [
            IssueRef("PROJ-1", "Alpha", "PROJ", "Project One"),
            IssueRef("PROJ-2", "Beta",  "PROJ", "Project One"),
            IssueRef("SUPP-9", "Gamma", "SUPP", "Support"),
        ]

    @responses.activate
    def test_two_pages_yields_all_issues_and_sends_token(
        self, service_account_auth: ServiceAccountAuth
    ) -> None:
        responses.add(
            responses.POST, _SEARCH_URL,
            json={"issues": [_ISSUE_1, _ISSUE_2, _ISSUE_3], "nextPageToken": "tok-p2"},
            status=200,
        )
        responses.add(
            responses.POST, _SEARCH_URL,
            json={"issues": [_ISSUE_4, _ISSUE_5]},
            status=200,
        )
        with JiraCloudClient.from_auth(service_account_auth) as client:
            result = list(iter_issues(client, "jql"))
        assert len(result) == 5
        second_body = json.loads(responses.calls[1].request.body)
        assert second_body["nextPageToken"] == "tok-p2"

    @responses.activate
    def test_empty_results_yields_nothing(
        self, service_account_auth: ServiceAccountAuth
    ) -> None:
        responses.add(responses.POST, _SEARCH_URL, json={"issues": []}, status=200)
        with JiraCloudClient.from_auth(service_account_auth) as client:
            result = list(iter_issues(client, "jql"))
        assert result == []

    @responses.activate
    def test_first_request_omits_next_page_token(
        self, service_account_auth: ServiceAccountAuth
    ) -> None:
        responses.add(
            responses.POST, _SEARCH_URL,
            json={"issues": [_ISSUE_1]},
            status=200,
        )
        with JiraCloudClient.from_auth(service_account_auth) as client:
            list(iter_issues(client, "jql"))
        first_body = json.loads(responses.calls[0].request.body)
        assert "nextPageToken" not in first_body
