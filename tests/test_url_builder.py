"""Tests for jwe.api.url_builder.

These guard the most subtle architectural decision: which base URL goes with
which auth mode. A regression here results in silent 401s, so the tests are
strict about the exact URL form.
"""

from __future__ import annotations

import pytest

from jwe.api.auth import (
    AuthHeaderStyle,
    ServiceAccountAuth,
    UserTokenAuth,
)
from jwe.api.url_builder import URLBuilder, validate_cloud_id, validate_site_url


class TestURLBuilderForServiceAccount:
    def test_uses_platform_gateway(
        self, service_account_auth: ServiceAccountAuth
    ) -> None:
        ub = URLBuilder.for_auth(service_account_auth)

        assert ub.base_url == (
            "https://api.atlassian.com/ex/jira/1a11d016-8984-4c3e-b9ab-142dd06acb1b"
        )

    def test_build_joins_path(self, service_account_auth: ServiceAccountAuth) -> None:
        ub = URLBuilder.for_auth(service_account_auth)

        assert ub.build("/rest/api/3/myself") == (
            "https://api.atlassian.com/ex/jira/"
            "1a11d016-8984-4c3e-b9ab-142dd06acb1b/rest/api/3/myself"
        )

    def test_invalid_cloud_id_rejected(self) -> None:
        bad_auth = ServiceAccountAuth(
            email="x@serviceaccount.atlassian.com",
            token="t",
            cloud_id="not-a-uuid",
            header_style=AuthHeaderStyle.BASIC,
        )
        with pytest.raises(ValueError, match="Invalid cloud_id"):
            URLBuilder.for_auth(bad_auth)


class TestURLBuilderForUserToken:
    def test_uses_site_url(self, user_token_auth: UserTokenAuth) -> None:
        ub = URLBuilder.for_auth(user_token_auth)

        assert ub.base_url == "https://acme.atlassian.net"

    def test_build_joins_path(self, user_token_auth: UserTokenAuth) -> None:
        ub = URLBuilder.for_auth(user_token_auth)

        assert ub.build("/rest/api/3/myself") == (
            "https://acme.atlassian.net/rest/api/3/myself"
        )

    def test_invalid_site_url_rejected(self) -> None:
        bad_auth = UserTokenAuth(
            email="x@example.com",
            token="t",
            site_url="https://acme.atlassian.net/",  # trailing slash
        )
        with pytest.raises(ValueError, match="Invalid site_url"):
            URLBuilder.for_auth(bad_auth)


class TestURLBuilderBuild:
    def test_path_must_start_with_slash(self) -> None:
        ub = URLBuilder(base_url="https://example.com")
        with pytest.raises(ValueError, match="must start with"):
            ub.build("rest/api/3/myself")

    def test_empty_path_rejected(self) -> None:
        ub = URLBuilder(base_url="https://example.com")
        with pytest.raises(ValueError, match="must not be empty"):
            ub.build("")

    def test_strips_trailing_slash_from_base(self) -> None:
        ub = URLBuilder(base_url="https://example.com/")
        assert ub.build("/foo") == "https://example.com/foo"


class TestValidators:
    @pytest.mark.parametrize(
        "valid",
        [
            "1a11d016-8984-4c3e-b9ab-142dd06acb1b",
            "12345678-1234-1234-1234-123456789abc",
        ],
    )
    def test_validate_cloud_id_accepts_uuids(self, valid: str) -> None:
        validate_cloud_id(valid)  # no exception

    @pytest.mark.parametrize(
        "invalid",
        [
            "",
            "not-a-uuid",
            "1a11d016-8984-4c3e-b9ab-142dd06acb1bX",  # extra char
            "1a11d016_8984_4c3e_b9ab_142dd06acb1b",  # underscores
            "1A11D016-8984-4C3E-B9AB-142DD06ACB1B",  # upper case (Atlassian uses lower)
        ],
    )
    def test_validate_cloud_id_rejects_garbage(self, invalid: str) -> None:
        with pytest.raises(ValueError):
            validate_cloud_id(invalid)

    @pytest.mark.parametrize(
        "valid",
        [
            "https://acme.atlassian.net",
            "https://my-company.atlassian.net",
            "https://x.atlassian.net",
        ],
    )
    def test_validate_site_url_accepts_well_formed(self, valid: str) -> None:
        validate_site_url(valid)  # no exception

    @pytest.mark.parametrize(
        "invalid",
        [
            "",
            "http://acme.atlassian.net",  # http not https
            "https://acme.atlassian.net/",  # trailing slash
            "https://acme.atlassian.net/jira",  # path
            "https://acme.com",  # wrong domain
            "acme.atlassian.net",  # no scheme
        ],
    )
    def test_validate_site_url_rejects_bad(self, invalid: str) -> None:
        with pytest.raises(ValueError):
            validate_site_url(invalid)
