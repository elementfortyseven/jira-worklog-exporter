"""Tests for jwe.api.tenant_info.

We mock HTTP via the ``responses`` library so the tests don't hit a real
Atlassian endpoint.
"""

from __future__ import annotations

import pytest
import responses

from jwe.api.tenant_info import TenantInfoError, discover_cloud_id


class TestDiscoverCloudId:
    @responses.activate
    def test_happy_path(self) -> None:
        responses.add(
            responses.GET,
            "https://acme.atlassian.net/_edge/tenant_info",
            json={"cloudId": "1a11d016-8984-4c3e-b9ab-142dd06acb1b"},
            status=200,
        )

        result = discover_cloud_id("https://acme.atlassian.net")

        assert result.cloud_id == "1a11d016-8984-4c3e-b9ab-142dd06acb1b"

    @responses.activate
    def test_404_raises(self) -> None:
        responses.add(
            responses.GET,
            "https://nope.atlassian.net/_edge/tenant_info",
            status=404,
        )

        with pytest.raises(TenantInfoError, match="returned HTTP 404"):
            discover_cloud_id("https://nope.atlassian.net")

    @responses.activate
    def test_missing_cloud_id_field_raises(self) -> None:
        responses.add(
            responses.GET,
            "https://acme.atlassian.net/_edge/tenant_info",
            json={"somethingElse": "value"},
            status=200,
        )

        with pytest.raises(TenantInfoError, match="did not include a 'cloudId' field"):
            discover_cloud_id("https://acme.atlassian.net")

    @responses.activate
    def test_non_json_response_raises(self) -> None:
        responses.add(
            responses.GET,
            "https://acme.atlassian.net/_edge/tenant_info",
            body="<html>error</html>",
            status=200,
            content_type="text/html",
        )

        with pytest.raises(TenantInfoError, match="non-JSON"):
            discover_cloud_id("https://acme.atlassian.net")

    def test_invalid_site_url_rejected_before_request(self) -> None:
        # No responses.add — if we made an HTTP request, it would fail loudly.
        with pytest.raises(ValueError, match="Invalid site_url"):
            discover_cloud_id("not-a-url")

    @pytest.mark.parametrize(
        "bypass_url",
        [
            "https://acme.atlassian.net.evil.com",  # suffix attack
            "https://acme.atlassian.net@evil.com",  # userinfo attack
        ],
    )
    def test_bypass_attempts_rejected_before_request(self, bypass_url: str) -> None:
        # Security control (JWE-22): allowlist validation must fire before any HTTP call.
        # No responses.add — a live request would fail the test if validation is skipped.
        with pytest.raises(ValueError, match="Invalid site_url"):
            discover_cloud_id(bypass_url)
