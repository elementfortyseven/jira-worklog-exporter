"""Tests for jwe.service."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from unittest import mock

import pytest
import responses as responses_lib

import jwe.service as service
from jwe.api.auth import AuthMode
from jwe.api.client import AuthenticationError, JiraPermissionError
from jwe.api.tenant_info import TenantInfo
from jwe.api.user import User
from jwe.config import ExportConfig
from jwe.exporter import ExportProgress, ExportResult

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_CLOUD_ID = "1a11d016-8984-4c3e-b9ab-142dd06acb1b"
_SA_BASE = f"https://api.atlassian.com/ex/jira/{_CLOUD_ID}"
_MYSELF_URL = f"{_SA_BASE}/rest/api/3/myself"
_USER_SEARCH_URL = f"{_SA_BASE}/rest/api/3/user/search"
_SEARCH_URL = f"{_SA_BASE}/rest/api/3/search/jql"
_SITE_URL = "https://acme.atlassian.net"
_TENANT_INFO_URL = f"{_SITE_URL}/_edge/tenant_info"

_SA_EMAIL = "bot@serviceaccount.atlassian.com"
_SA_TOKEN = "ATATT3xFfGF0dummy_service_account_token"

_MYSELF: dict[str, object] = {
    "accountId": "5b10ac8d82e05b22cc7d4ef5",
    "displayName": "Jira Bot",
    "emailAddress": _SA_EMAIL,
    "active": True,
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _sa_config(tmp_path: Path) -> ExportConfig:
    return ExportConfig(
        auth_mode=AuthMode.SERVICE_ACCOUNT,
        cloud_id=_CLOUD_ID,
        service_account_email=_SA_EMAIL,
        api_token=_SA_TOKEN,
        user_account_ids=["user-001"],
        from_date=date(2026, 4, 1),
        to_date=date(2026, 4, 30),
        output_dir=tmp_path,
    )


def _atlassian_user(aid: str, name: str) -> dict[str, object]:
    return {
        "accountId": aid,
        "displayName": name,
        "emailAddress": f"{aid}@example.com",
        "active": True,
        "accountType": "atlassian",
    }


# ---------------------------------------------------------------------------
# test_connection
# ---------------------------------------------------------------------------


class TestTestConnection:
    @responses_lib.activate
    def test_happy_path_returns_user(self, tmp_path: Path) -> None:
        responses_lib.add(responses_lib.GET, _MYSELF_URL, json=_MYSELF)

        user = service.test_connection(_sa_config(tmp_path))

        assert isinstance(user, User)
        assert user.account_id == "5b10ac8d82e05b22cc7d4ef5"
        assert user.display_name == "Jira Bot"
        assert user.email == _SA_EMAIL

    @responses_lib.activate
    def test_http_401_raises_authentication_error(self, tmp_path: Path) -> None:
        responses_lib.add(
            responses_lib.GET,
            _MYSELF_URL,
            status=401,
            json={"errorMessages": ["Unauthorized"]},
        )

        with pytest.raises(AuthenticationError):
            service.test_connection(_sa_config(tmp_path))

    @responses_lib.activate
    def test_http_403_raises_permission_error(self, tmp_path: Path) -> None:
        responses_lib.add(
            responses_lib.GET,
            _MYSELF_URL,
            status=403,
            json={"errorMessages": ["Forbidden"]},
        )

        with pytest.raises(JiraPermissionError):
            service.test_connection(_sa_config(tmp_path))


# ---------------------------------------------------------------------------
# search_users
# ---------------------------------------------------------------------------


class TestSearchUsers:
    @responses_lib.activate
    def test_three_results_returned(self, tmp_path: Path) -> None:
        responses_lib.add(
            responses_lib.GET,
            _USER_SEARCH_URL,
            json=[
                _atlassian_user("aid1", "Alice"),
                _atlassian_user("aid2", "Bob"),
                _atlassian_user("aid3", "Carol"),
            ],
        )

        users = service.search_users(_sa_config(tmp_path), query="example.com")

        assert len(users) == 3
        assert [u.display_name for u in users] == ["Alice", "Bob", "Carol"]


# ---------------------------------------------------------------------------
# discover_cloud_id
# ---------------------------------------------------------------------------


class TestDiscoverCloudId:
    @responses_lib.activate
    def test_returns_tenant_info(self) -> None:
        responses_lib.add(
            responses_lib.GET,
            _TENANT_INFO_URL,
            json={"cloudId": _CLOUD_ID},
        )

        result = service.discover_cloud_id(_SITE_URL)

        assert isinstance(result, TenantInfo)
        assert result.cloud_id == _CLOUD_ID


# ---------------------------------------------------------------------------
# Token persistence
# ---------------------------------------------------------------------------


class TestTokenPersistence:
    def test_save_load_delete_key_schema(self) -> None:
        mock_kr = mock.MagicMock()
        mock_kr.get_password.return_value = "test-token"

        with mock.patch.object(service, "keyring", mock_kr):
            service.save_token(AuthMode.SERVICE_ACCOUNT, _CLOUD_ID, "test-token")
            token = service.load_token(AuthMode.SERVICE_ACCOUNT, _CLOUD_ID)
            service.delete_token(AuthMode.SERVICE_ACCOUNT, _CLOUD_ID)

        expected_key = f"jwe:service-account:{_CLOUD_ID}"
        mock_kr.set_password.assert_called_once_with("jwe", expected_key, "test-token")
        mock_kr.get_password.assert_called_once_with("jwe", expected_key)
        mock_kr.delete_password.assert_called_once_with("jwe", expected_key)
        assert token == "test-token"

    def test_load_not_found_returns_none(self) -> None:
        mock_kr = mock.MagicMock()
        mock_kr.get_password.return_value = None

        with mock.patch.object(service, "keyring", mock_kr):
            result = service.load_token(AuthMode.USER_TOKEN, _SITE_URL)

        assert result is None

    def test_save_without_keyring_raises_runtime_error(self) -> None:
        with mock.patch.object(service, "keyring", None), pytest.raises(RuntimeError, match="keyring"):
            service.save_token(AuthMode.SERVICE_ACCOUNT, _CLOUD_ID, "tok")

    def test_load_without_keyring_raises_runtime_error(self) -> None:
        with mock.patch.object(service, "keyring", None), pytest.raises(RuntimeError, match="keyring"):
            service.load_token(AuthMode.SERVICE_ACCOUNT, _CLOUD_ID)

    def test_delete_without_keyring_raises_runtime_error(self) -> None:
        with mock.patch.object(service, "keyring", None), pytest.raises(RuntimeError, match="keyring"):
            service.delete_token(AuthMode.SERVICE_ACCOUNT, _CLOUD_ID)

    def test_delete_missing_token_is_idempotent(self) -> None:
        # Backends (e.g. the Windows credential store) raise when the entry is
        # absent; delete_token must treat that as a no-op, not propagate (JWE-51).
        mock_kr = mock.MagicMock()
        mock_kr.delete_password.side_effect = Exception("no such entry")

        with mock.patch.object(service, "keyring", mock_kr):
            service.delete_token(AuthMode.SERVICE_ACCOUNT, _CLOUD_ID)  # must not raise

        expected_key = f"jwe:service-account:{_CLOUD_ID}"
        mock_kr.delete_password.assert_called_once_with("jwe", expected_key)


# ---------------------------------------------------------------------------
# config_from_env
# ---------------------------------------------------------------------------


class TestConfigFromEnv:
    def test_env_vars_map_to_config(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("JWE_AUTH_MODE", "user-token")
        monkeypatch.setenv("JWE_SITE_URL", _SITE_URL)
        monkeypatch.setenv("JWE_EMAIL", "user@example.com")

        cfg = service.config_from_env()

        assert cfg.auth_mode == AuthMode.USER_TOKEN
        assert cfg.site_url == _SITE_URL
        assert cfg.email == "user@example.com"


# ---------------------------------------------------------------------------
# run_export re-export
# ---------------------------------------------------------------------------


class TestRunExportReExport:
    @responses_lib.activate
    def test_produces_export_result(self, tmp_path: Path) -> None:
        """service.run_export delegates to exporter.run_export correctly."""
        responses_lib.add(responses_lib.GET, _MYSELF_URL, json=_MYSELF)
        responses_lib.add(responses_lib.POST, _SEARCH_URL, json={"issues": []})

        events = list(service.run_export(_sa_config(tmp_path)))

        result = next(e for e in events if isinstance(e, ExportResult))
        assert result.issues_seen == 0
        assert result.worklogs_written == 0
        assert isinstance(events[-1], ExportResult)
        assert any(isinstance(e, ExportProgress) for e in events)
