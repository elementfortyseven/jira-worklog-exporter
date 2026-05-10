"""Tests for jwe.api.auth.

These cover the architectural foundation: header construction, identity
labels, and — crucially — the no-token-leak property in repr().
"""

from __future__ import annotations

import base64

import pytest

from jwe.api.auth import (
    AuthMode,
    ServiceAccountAuth,
    UserTokenAuth,
    _mask_token,
)


class TestServiceAccountAuth:
    def test_mode_is_service_account(
        self, service_account_auth: ServiceAccountAuth
    ) -> None:
        assert service_account_auth.mode is AuthMode.SERVICE_ACCOUNT

    def test_basic_authorization_header_is_base64_encoded(
        self, service_account_auth: ServiceAccountAuth
    ) -> None:
        header = service_account_auth.authorization_header()

        assert header.startswith("Basic ")
        decoded = base64.b64decode(header.removeprefix("Basic ")).decode("ascii")
        assert decoded == (
            "jwe-bot@serviceaccount.atlassian.com:"
            "ATATT3xFfGF0dummy_service_account_token_value"
        )

    def test_bearer_authorization_header_is_plain(
        self, service_account_auth_bearer: ServiceAccountAuth
    ) -> None:
        header = service_account_auth_bearer.authorization_header()

        assert header == "Bearer ATATT3xFfGF0dummy_service_account_token_value"

    def test_identity_label_includes_email(
        self, service_account_auth: ServiceAccountAuth
    ) -> None:
        assert (
            service_account_auth.identity_label()
            == "service-account:jwe-bot@serviceaccount.atlassian.com"
        )

    def test_repr_masks_token(self, service_account_auth: ServiceAccountAuth) -> None:
        text = repr(service_account_auth)

        # Token must not appear in any form
        assert "ATATT3xFfGF0dummy_service_account_token_value" not in text
        # But other fields should be present for debugging
        assert "jwe-bot@serviceaccount.atlassian.com" in text
        assert "1a11d016-8984-4c3e-b9ab-142dd06acb1b" in text
        assert "basic" in text.lower()


class TestUserTokenAuth:
    def test_mode_is_user_token(self, user_token_auth: UserTokenAuth) -> None:
        assert user_token_auth.mode is AuthMode.USER_TOKEN

    def test_authorization_header_is_basic(self, user_token_auth: UserTokenAuth) -> None:
        header = user_token_auth.authorization_header()

        assert header.startswith("Basic ")
        decoded = base64.b64decode(header.removeprefix("Basic ")).decode("ascii")
        assert decoded == "martin@example.com:ATATT3xFfGF0dummy_personal_token_value"

    def test_identity_label_includes_email(self, user_token_auth: UserTokenAuth) -> None:
        assert user_token_auth.identity_label() == "user-token:martin@example.com"

    def test_repr_masks_token(self, user_token_auth: UserTokenAuth) -> None:
        text = repr(user_token_auth)

        assert "ATATT3xFfGF0dummy_personal_token_value" not in text
        assert "martin@example.com" in text
        assert "https://acme.atlassian.net" in text


class TestMaskToken:
    @pytest.mark.parametrize(
        ("token", "expected"),
        [
            ("short", "***"),
            ("01234567890", "***"),  # 11 chars — still too short
            ("012345678901", "0123…8901"),  # 12 chars — first 4, last 4
            ("ATATT3xFfGF0abcdefghijklmnop", "ATAT…mnop"),
        ],
    )
    def test_mask_token(self, token: str, expected: str) -> None:
        assert _mask_token(token) == expected
