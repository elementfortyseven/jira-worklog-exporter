"""Cloud ID discovery from a Jira site URL.

Every Atlassian Cloud site exposes an unauthenticated endpoint at
``/_edge/tenant_info`` that returns the site's cloud ID. This is the easiest
way for users to look up their cloud ID without navigating the admin console.

Used by:

* The CLI subcommand ``--discover-cloud-id <site-url>``.
* The GUI helper button "Aus Site-URL ermitteln".

This module deliberately does not authenticate. It also does not retry —
the call is cheap and a single failure is informative.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import requests

from jwe.api.url_builder import validate_site_url

logger = logging.getLogger(__name__)

DISCOVERY_TIMEOUT_SECONDS = 10
"""Conservative timeout for the discovery call. The endpoint is fast in practice."""


class TenantInfoError(Exception):
    """Raised when cloud ID discovery fails."""


@dataclass(frozen=True)
class TenantInfo:
    """Result of a successful tenant_info lookup."""

    cloud_id: str
    """The site's cloud ID (UUID)."""


def discover_cloud_id(site_url: str, timeout: float = DISCOVERY_TIMEOUT_SECONDS) -> TenantInfo:
    """Look up the cloud ID for a Jira Cloud site.

    Args:
        site_url: The site's base URL, e.g. ``https://acme.atlassian.net``
            (no trailing slash, no path).
        timeout: HTTP timeout in seconds.

    Returns:
        A :class:`TenantInfo` with the cloud ID.

    Raises:
        ValueError: if ``site_url`` is malformed.
        TenantInfoError: if the endpoint is unreachable, returns a non-200,
            or omits the ``cloudId`` field.
    """
    validate_site_url(site_url)
    url = f"{site_url.rstrip('/')}/_edge/tenant_info"

    logger.debug("Discovering cloud ID via %s", url)
    try:
        response = requests.get(url, timeout=timeout, allow_redirects=False)
    except requests.RequestException as exc:
        raise TenantInfoError(f"Could not reach {url}: {exc}") from exc

    if response.status_code != 200:
        raise TenantInfoError(
            f"{url} returned HTTP {response.status_code}. "
            "Verify the site URL is correct and the site is reachable."
        )

    try:
        payload = response.json()
    except ValueError as exc:
        raise TenantInfoError(f"{url} returned non-JSON payload") from exc

    cloud_id = payload.get("cloudId")
    if not isinstance(cloud_id, str) or not cloud_id:
        raise TenantInfoError(
            f"{url} response did not include a 'cloudId' field. "
            f"Got: {payload!r}"
        )

    logger.info("Resolved cloud ID for %s: %s", site_url, cloud_id)
    return TenantInfo(cloud_id=cloud_id)
