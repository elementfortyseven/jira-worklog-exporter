"""Tests for jwe.config.ExportConfig."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from jwe.api.auth import AuthHeaderStyle, AuthMode
from jwe.config import ColumnProfile, ExportConfig

_CLOUD_ID = "1a11d016-8984-4c3e-b9ab-142dd06acb1b"
_SA_EMAIL = "bot@serviceaccount.atlassian.com"
_USER_EMAIL = "martin@example.com"
_SITE_URL = "https://acme.atlassian.net"
_TOKEN = "ATATT3xFfGF0dummy_token_value_long_enough"
_FROM = date(2026, 4, 1)
_TO = date(2026, 4, 30)


def _sa_config(tmp_path: Path, **overrides: object) -> ExportConfig:
    """Return a valid SERVICE_ACCOUNT config rooted in tmp_path."""
    defaults: dict[str, object] = dict(
        auth_mode=AuthMode.SERVICE_ACCOUNT,
        cloud_id=_CLOUD_ID,
        service_account_email=_SA_EMAIL,
        api_token=_TOKEN,
        user_account_ids=["aid1"],
        from_date=_FROM,
        to_date=_TO,
        output_dir=tmp_path,
    )
    defaults.update(overrides)
    return ExportConfig(**defaults)  # type: ignore[arg-type]


def _ut_config(tmp_path: Path, **overrides: object) -> ExportConfig:
    """Return a valid USER_TOKEN config rooted in tmp_path."""
    defaults: dict[str, object] = dict(
        auth_mode=AuthMode.USER_TOKEN,
        site_url=_SITE_URL,
        email=_USER_EMAIL,
        api_token=_TOKEN,
        user_account_ids=["aid1"],
        from_date=_FROM,
        to_date=_TO,
        output_dir=tmp_path,
    )
    defaults.update(overrides)
    return ExportConfig(**defaults)  # type: ignore[arg-type]


class TestValidateHappyPath:
    def test_service_account_valid(self, tmp_path: Path) -> None:
        _sa_config(tmp_path).validate()

    def test_user_token_valid(self, tmp_path: Path) -> None:
        _ut_config(tmp_path).validate()


class TestValidateUserAccountIds:
    def test_empty_raises(self, tmp_path: Path) -> None:
        cfg = _sa_config(tmp_path, user_account_ids=[])
        with pytest.raises(ValueError, match="user_account_ids"):
            cfg.validate()


class TestValidateDates:
    def test_missing_from_date_raises(self, tmp_path: Path) -> None:
        cfg = _sa_config(tmp_path, from_date=None)
        with pytest.raises(ValueError, match="from_date"):
            cfg.validate()

    def test_missing_to_date_raises(self, tmp_path: Path) -> None:
        cfg = _sa_config(tmp_path, to_date=None)
        with pytest.raises(ValueError, match="to_date"):
            cfg.validate()

    def test_from_after_to_raises(self, tmp_path: Path) -> None:
        cfg = _sa_config(tmp_path, from_date=date(2026, 5, 1), to_date=date(2026, 4, 1))
        with pytest.raises(ValueError, match="from_date"):
            cfg.validate()

    def test_same_day_is_valid(self, tmp_path: Path) -> None:
        _sa_config(tmp_path, from_date=_FROM, to_date=_FROM).validate()


class TestValidateApiToken:
    def test_empty_token_raises(self, tmp_path: Path) -> None:
        cfg = _sa_config(tmp_path, api_token="")
        with pytest.raises(ValueError, match="api_token"):
            cfg.validate()


class TestValidateServiceAccount:
    def test_invalid_cloud_id_raises(self, tmp_path: Path) -> None:
        cfg = _sa_config(tmp_path, cloud_id="not-a-uuid")
        with pytest.raises(ValueError, match="cloud_id"):
            cfg.validate()

    def test_empty_service_account_email_raises(self, tmp_path: Path) -> None:
        cfg = _sa_config(tmp_path, service_account_email="")
        with pytest.raises(ValueError, match="service_account_email"):
            cfg.validate()

    def test_email_wrong_domain_raises(self, tmp_path: Path) -> None:
        cfg = _sa_config(tmp_path, service_account_email="bot@example.com")
        with pytest.raises(ValueError, match=r"serviceaccount\.atlassian\.com"):
            cfg.validate()


class TestValidateUserToken:
    def test_invalid_site_url_raises(self, tmp_path: Path) -> None:
        cfg = _ut_config(tmp_path, site_url="https://acme.example.com")
        with pytest.raises(ValueError, match="site_url"):
            cfg.validate()

    def test_empty_email_raises(self, tmp_path: Path) -> None:
        cfg = _ut_config(tmp_path, email="")
        with pytest.raises(ValueError, match="email"):
            cfg.validate()

    def test_email_without_at_raises(self, tmp_path: Path) -> None:
        cfg = _ut_config(tmp_path, email="notanemail")
        with pytest.raises(ValueError, match="@"):
            cfg.validate()


class TestValidateProjectKeys:
    def test_lowercase_key_raises(self, tmp_path: Path) -> None:
        cfg = _sa_config(tmp_path, project_keys=["proj"])
        with pytest.raises(ValueError, match="proj"):
            cfg.validate()

    def test_valid_keys_pass(self, tmp_path: Path) -> None:
        _sa_config(tmp_path, project_keys=["PROJ", "SUPP2", "MY_PROJECT"]).validate()


class TestValidateDelimiter:
    def test_pipe_delimiter_raises(self, tmp_path: Path) -> None:
        cfg = _sa_config(tmp_path, delimiter="|")
        with pytest.raises(ValueError, match="delimiter"):
            cfg.validate()

    def test_semicolon_delimiter_is_valid(self, tmp_path: Path) -> None:
        _sa_config(tmp_path, delimiter=";").validate()


class TestValidateApiVersion:
    def test_version_1_raises(self, tmp_path: Path) -> None:
        cfg = _sa_config(tmp_path, api_version=1)
        with pytest.raises(ValueError, match="api_version"):
            cfg.validate()

    def test_version_2_is_valid(self, tmp_path: Path) -> None:
        _sa_config(tmp_path, api_version=2).validate()


class TestValidateOutputDir:
    def test_nonexistent_dir_raises(self, tmp_path: Path) -> None:
        cfg = _sa_config(tmp_path, output_dir=tmp_path / "does_not_exist")
        with pytest.raises(ValueError, match="output_dir"):
            cfg.validate()

    def test_existing_dir_passes(self, tmp_path: Path) -> None:
        _sa_config(tmp_path, output_dir=tmp_path).validate()


class TestToRedactedDict:
    def test_token_is_redacted(self, tmp_path: Path) -> None:
        result = _sa_config(tmp_path).to_redacted_dict()
        assert result["api_token"] == "***"

    def test_other_fields_are_plaintext(self, tmp_path: Path) -> None:
        result = _sa_config(tmp_path).to_redacted_dict()
        assert result["cloud_id"] == _CLOUD_ID
        assert result["service_account_email"] == _SA_EMAIL

    def test_auth_mode_enum_becomes_value_string(self, tmp_path: Path) -> None:
        result = _sa_config(tmp_path).to_redacted_dict()
        assert result["auth_mode"] == "service-account"

    def test_column_profile_enum_becomes_value_string(self, tmp_path: Path) -> None:
        result = _sa_config(tmp_path, column_profile=ColumnProfile.FULL).to_redacted_dict()
        assert result["column_profile"] == "full"

    def test_auth_header_enum_becomes_value_string(self, tmp_path: Path) -> None:
        result = _sa_config(tmp_path, auth_header=AuthHeaderStyle.BEARER).to_redacted_dict()
        assert result["auth_header"] == "bearer"

    def test_output_dir_becomes_string(self, tmp_path: Path) -> None:
        result = _sa_config(tmp_path).to_redacted_dict()
        assert isinstance(result["output_dir"], str)
        assert result["output_dir"] == str(tmp_path)

    def test_dates_become_iso_strings(self, tmp_path: Path) -> None:
        result = _sa_config(tmp_path).to_redacted_dict()
        assert result["from_date"] == "2026-04-01"
        assert result["to_date"] == "2026-04-30"

    def test_none_dates_remain_none(self, tmp_path: Path) -> None:
        cfg = ExportConfig()
        result = cfg.to_redacted_dict()
        assert result["from_date"] is None
        assert result["to_date"] is None
