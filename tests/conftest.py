"""Shared pytest fixtures."""

from __future__ import annotations

import pytest

from jwe.api.auth import (
    AuthHeaderStyle,
    ServiceAccountAuth,
    UserTokenAuth,
)


@pytest.fixture
def service_account_auth() -> ServiceAccountAuth:
    """A ServiceAccountAuth with realistic-looking dummy values."""
    return ServiceAccountAuth(
        email="jwe-bot@serviceaccount.atlassian.com",
        token="ATATT3xFfGF0dummy_service_account_token_value",
        cloud_id="1a11d016-8984-4c3e-b9ab-142dd06acb1b",
        header_style=AuthHeaderStyle.BASIC,
    )


@pytest.fixture
def service_account_auth_bearer() -> ServiceAccountAuth:
    """A ServiceAccountAuth using Bearer auth instead of Basic."""
    return ServiceAccountAuth(
        email="jwe-bot@serviceaccount.atlassian.com",
        token="ATATT3xFfGF0dummy_service_account_token_value",
        cloud_id="1a11d016-8984-4c3e-b9ab-142dd06acb1b",
        header_style=AuthHeaderStyle.BEARER,
    )


@pytest.fixture
def user_token_auth() -> UserTokenAuth:
    """A UserTokenAuth with realistic-looking dummy values."""
    return UserTokenAuth(
        email="martin@example.com",
        token="ATATT3xFfGF0dummy_personal_token_value",
        site_url="https://acme.atlassian.net",
    )
