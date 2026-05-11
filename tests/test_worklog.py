"""Tests for jwe.api.worklog."""

from __future__ import annotations

from datetime import date, datetime, time
from typing import Any
from urllib.parse import parse_qs, urlparse

import responses

from jwe.api.auth import ServiceAccountAuth
from jwe.api.client import JiraCloudClient
from jwe.api.worklog import Worklog, iter_worklogs

_CLOUD_ID = "1a11d016-8984-4c3e-b9ab-142dd06acb1b"
_SA_BASE = f"https://api.atlassian.com/ex/jira/{_CLOUD_ID}"
_ISSUE_KEY = "PROJ-42"
_WORKLOG_URL = f"{_SA_BASE}/rest/api/3/issue/{_ISSUE_KEY}/worklog"

_FROM = date(2026, 4, 1)
_TO = date(2026, 4, 30)
_ACCOUNTS = {"user-001", "user-002", "user-003"}


def _wl(
    wl_id: str = "1001",
    account_id: str = "user-001",
    *,
    email: str | None = "user@example.com",
    comment: object = None,
) -> dict[str, Any]:
    author: dict[str, Any] = {"accountId": account_id, "displayName": f"User {account_id}"}
    if email is not None:
        author["emailAddress"] = email
    entry: dict[str, Any] = {
        "id": wl_id,
        "author": author,
        "started": "2026-04-15T10:00:00.000+0000",
        "timeSpent": "1h",
        "timeSpentSeconds": 3600,
        "created": "2026-04-15T10:05:00.000+0000",
        "updated": "2026-04-15T10:05:00.000+0000",
    }
    if comment is not None:
        entry["comment"] = comment
    return entry


def _page(
    worklogs: list[dict[str, Any]],
    start_at: int = 0,
    max_results: int = 1000,
    total: int | None = None,
) -> dict[str, Any]:
    return {
        "worklogs": worklogs,
        "startAt": start_at,
        "maxResults": max_results,
        "total": total if total is not None else len(worklogs),
    }


class TestIterWorklogs:
    @responses.activate
    def test_single_page_three_matching_authors_yields_three(
        self, service_account_auth: ServiceAccountAuth
    ) -> None:
        responses.add(
            responses.GET,
            _WORKLOG_URL,
            json=_page([_wl("1001", "user-001"), _wl("1002", "user-002"), _wl("1003", "user-003")]),
            status=200,
        )
        with JiraCloudClient.from_auth(service_account_auth) as client:
            result = list(iter_worklogs(client, _ISSUE_KEY, _FROM, _TO, _ACCOUNTS))
        assert len(result) == 3
        assert all(isinstance(w, Worklog) for w in result)
        assert [w.id for w in result] == ["1001", "1002", "1003"]

    @responses.activate
    def test_two_pages_accumulates_all_and_second_request_has_correct_start_at(
        self, service_account_auth: ServiceAccountAuth
    ) -> None:
        page_size = 2
        responses.add(
            responses.GET,
            _WORKLOG_URL,
            json=_page(
                [_wl("1001", "user-001"), _wl("1002", "user-002")],
                start_at=0,
                max_results=page_size,
                total=3,
            ),
            status=200,
        )
        responses.add(
            responses.GET,
            _WORKLOG_URL,
            json=_page(
                [_wl("1003", "user-003")],
                start_at=page_size,
                max_results=page_size,
                total=3,
            ),
            status=200,
        )
        with JiraCloudClient.from_auth(service_account_auth) as client:
            result = list(iter_worklogs(client, _ISSUE_KEY, _FROM, _TO, _ACCOUNTS, page_size=page_size))
        assert len(result) == 3
        assert len(responses.calls) == 2
        second_qs = parse_qs(urlparse(responses.calls[1].request.url).query)
        assert second_qs["startAt"] == [str(page_size)]

    @responses.activate
    def test_foreign_account_id_is_filtered_out(
        self, service_account_auth: ServiceAccountAuth
    ) -> None:
        responses.add(
            responses.GET,
            _WORKLOG_URL,
            json=_page([_wl("1001", "user-001"), _wl("1002", "user-FOREIGN"), _wl("1003", "user-003")]),
            status=200,
        )
        with JiraCloudClient.from_auth(service_account_auth) as client:
            result = list(iter_worklogs(client, _ISSUE_KEY, _FROM, _TO, _ACCOUNTS))
        assert len(result) == 2
        assert all(w.author_account_id in _ACCOUNTS for w in result)

    @responses.activate
    def test_missing_email_address_maps_to_empty_string(
        self, service_account_auth: ServiceAccountAuth
    ) -> None:
        responses.add(
            responses.GET,
            _WORKLOG_URL,
            json=_page([_wl("1001", email=None)]),
            status=200,
        )
        with JiraCloudClient.from_auth(service_account_auth) as client:
            result = list(iter_worklogs(client, _ISSUE_KEY, _FROM, _TO, _ACCOUNTS))
        assert result[0].author_email == ""

    @responses.activate
    def test_missing_comment_maps_to_none(
        self, service_account_auth: ServiceAccountAuth
    ) -> None:
        responses.add(
            responses.GET,
            _WORKLOG_URL,
            json=_page([_wl("1001")]),
            status=200,
        )
        with JiraCloudClient.from_auth(service_account_auth) as client:
            result = list(iter_worklogs(client, _ISSUE_KEY, _FROM, _TO, _ACCOUNTS))
        assert result[0].comment_adf is None

    @responses.activate
    def test_date_range_is_sent_as_plausible_epoch_ms(
        self, service_account_auth: ServiceAccountAuth
    ) -> None:
        responses.add(
            responses.GET,
            _WORKLOG_URL,
            json=_page([]),
            status=200,
        )
        with JiraCloudClient.from_auth(service_account_auth) as client:
            list(iter_worklogs(client, _ISSUE_KEY, _FROM, _TO, _ACCOUNTS))

        qs = parse_qs(urlparse(responses.calls[0].request.url).query)
        expected_after = int(datetime.combine(_FROM, time(0, 0, 0)).timestamp() * 1000)
        expected_before = int(datetime.combine(_TO, time(23, 59, 59, 999000)).timestamp() * 1000)
        assert qs["startedAfter"] == [str(expected_after)]
        assert qs["startedBefore"] == [str(expected_before)]
        assert expected_before > expected_after

    @responses.activate
    def test_empty_worklogs_yields_nothing(
        self, service_account_auth: ServiceAccountAuth
    ) -> None:
        responses.add(
            responses.GET,
            _WORKLOG_URL,
            json=_page([]),
            status=200,
        )
        with JiraCloudClient.from_auth(service_account_auth) as client:
            result = list(iter_worklogs(client, _ISSUE_KEY, _FROM, _TO, _ACCOUNTS))
        assert result == []

    @responses.activate
    def test_short_last_page_makes_no_extra_request(
        self, service_account_auth: ServiceAccountAuth
    ) -> None:
        page_size = 3
        responses.add(
            responses.GET,
            _WORKLOG_URL,
            json=_page(
                [_wl("1001"), _wl("1002")],
                max_results=page_size,
                total=2,
            ),
            status=200,
        )
        with JiraCloudClient.from_auth(service_account_auth) as client:
            result = list(iter_worklogs(client, _ISSUE_KEY, _FROM, _TO, _ACCOUNTS, page_size=page_size))
        assert len(result) == 2
        assert len(responses.calls) == 1
