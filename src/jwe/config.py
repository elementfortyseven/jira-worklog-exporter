"""Typed configuration for an export run.

Both the CLI (argparse) and GUI (Tk form) ultimately produce an
:class:`ExportConfig` and hand it to :func:`jwe.exporter.run_export`.
Validation lives in :meth:`ExportConfig.validate` so both entry points share
the same rules.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from enum import StrEnum
from pathlib import Path

from jwe.api.auth import (
    AuthHeaderStyle,
    AuthMode,
    AuthStrategy,
    ServiceAccountAuth,
    UserTokenAuth,
)
from jwe.api.url_builder import validate_cloud_id, validate_site_url

_PROJECT_KEY_RE = re.compile(r"^[A-Z][A-Z0-9_]+$")
_VALID_DELIMITERS = {",", ";"}
_VALID_API_VERSIONS = {2, 3}


class ColumnProfile(StrEnum):
    """Output column profile per PRD §8."""

    MINIMAL = "minimal"
    STANDARD = "standard"
    FULL = "full"


@dataclass
class ExportConfig:
    """All inputs needed for a single export run.

    Auth-mode-specific fields are only meaningful when the matching mode is
    selected; cross-field validation enforces this in :meth:`validate`.
    """

    # Auth
    auth_mode: AuthMode = AuthMode.SERVICE_ACCOUNT
    cloud_id: str = ""              # required if SERVICE_ACCOUNT
    service_account_email: str = ""  # required if SERVICE_ACCOUNT
    auth_header: AuthHeaderStyle = AuthHeaderStyle.BASIC
    site_url: str = ""              # required if USER_TOKEN
    email: str = ""                 # required if USER_TOKEN
    api_token: str = ""             # never logged

    # Filter
    user_account_ids: list[str] = field(default_factory=list)
    from_date: date | None = None
    to_date: date | None = None
    project_keys: list[str] = field(default_factory=list)

    # Output
    output_dir: Path = field(default_factory=lambda: Path.cwd())
    column_profile: ColumnProfile = ColumnProfile.STANDARD
    delimiter: str = ","

    # Behaviour
    api_version: int = 3
    verbose: bool = False
    dry_run: bool = False

    def validate(self) -> None:
        """Validate the config, raising :class:`ValueError` on the first issue."""
        if not self.user_account_ids:
            raise ValueError("user_account_ids must not be empty")

        if self.from_date is None:
            raise ValueError("from_date must be set")
        if self.to_date is None:
            raise ValueError("to_date must be set")
        if self.from_date > self.to_date:
            raise ValueError(
                f"from_date {self.from_date} must not be after to_date {self.to_date}"
            )

        if not self.api_token:
            raise ValueError("api_token must not be empty")

        if self.auth_mode is AuthMode.SERVICE_ACCOUNT:
            validate_cloud_id(self.cloud_id)
            if not self.service_account_email:
                raise ValueError("service_account_email must not be empty")
            if not self.service_account_email.endswith("@serviceaccount.atlassian.com"):
                raise ValueError(
                    f"service_account_email {self.service_account_email!r} must end with "
                    "'@serviceaccount.atlassian.com'"
                )
        elif self.auth_mode is AuthMode.USER_TOKEN:
            validate_site_url(self.site_url)
            if not self.email:
                raise ValueError("email must not be empty")
            if "@" not in self.email:
                raise ValueError(
                    f"email {self.email!r} does not look like an email address (missing '@')"
                )

        for key in self.project_keys:
            if not _PROJECT_KEY_RE.match(key):
                raise ValueError(
                    f"Invalid project key {key!r}. Must match ^[A-Z][A-Z0-9_]+$"
                )

        if self.delimiter not in _VALID_DELIMITERS:
            raise ValueError(
                f"delimiter {self.delimiter!r} is not valid. Must be ',' or ';'"
            )

        if self.api_version not in _VALID_API_VERSIONS:
            raise ValueError(
                f"api_version {self.api_version} is not valid. Must be 2 or 3"
            )

        if not self.output_dir.is_dir():
            raise ValueError(
                f"output_dir {str(self.output_dir)!r} does not exist or is not a directory"
            )

    def build_auth(self) -> AuthStrategy:
        """Build an :class:`~jwe.api.auth.AuthStrategy` from this config.

        Returns:
            A concrete :class:`~jwe.api.auth.AuthStrategy` matching
            :attr:`auth_mode`.

        Raises:
            RuntimeError: If a required field is empty. This cannot happen
                after a successful :meth:`validate` call.
        """
        if self.auth_mode is AuthMode.SERVICE_ACCOUNT:
            if not self.service_account_email or not self.api_token or not self.cloud_id:
                raise RuntimeError(
                    "SERVICE_ACCOUNT auth requires service_account_email, api_token, "
                    "and cloud_id. Call validate() before build_auth()."
                )
            return ServiceAccountAuth(
                email=self.service_account_email,
                token=self.api_token,
                cloud_id=self.cloud_id,
                header_style=self.auth_header,
            )
        if not self.email or not self.api_token or not self.site_url:
            raise RuntimeError(
                "USER_TOKEN auth requires email, api_token, and site_url. "
                "Call validate() before build_auth()."
            )
        return UserTokenAuth(
            email=self.email,
            token=self.api_token,
            site_url=self.site_url,
        )

    def to_redacted_dict(self) -> dict[str, object]:
        """Return a dict suitable for logging — token redacted."""
        return {
            "auth_mode": self.auth_mode.value,
            "cloud_id": self.cloud_id,
            "service_account_email": self.service_account_email,
            "auth_header": self.auth_header.value,
            "site_url": self.site_url,
            "email": self.email,
            "api_token": "***",
            "user_account_ids": self.user_account_ids,
            "from_date": self.from_date.isoformat() if self.from_date is not None else None,
            "to_date": self.to_date.isoformat() if self.to_date is not None else None,
            "project_keys": self.project_keys,
            "output_dir": str(self.output_dir),
            "column_profile": self.column_profile.value,
            "delimiter": self.delimiter,
            "api_version": self.api_version,
            "verbose": self.verbose,
            "dry_run": self.dry_run,
        }
