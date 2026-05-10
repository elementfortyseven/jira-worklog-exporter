"""Typed configuration for an export run.

Both the CLI (argparse) and GUI (Tk form) ultimately produce an
:class:`ExportConfig` and hand it to :func:`jwe.exporter.run_export`.
Validation lives in :meth:`ExportConfig.validate` so both entry points share
the same rules.

TODO (claude code):
1. Flesh out :class:`ExportConfig` with all fields named in PRD §11.
2. Add :meth:`validate` to enforce regex constraints (cloud_id, project_keys,
   site_url) and cross-field rules (e.g. ``cloud_id`` required iff
   ``auth_mode is SERVICE_ACCOUNT``).
3. Add :func:`from_env` for environment-variable defaults (PRD FR-08).
4. Add :func:`to_redacted_dict` for safe logging — never include the token.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import StrEnum
from pathlib import Path

from jwe.api.auth import AuthHeaderStyle, AuthMode


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
        """Validate the config, raising :class:`ValueError` on the first issue.

        TODO: implement per PRD §11 and §6.1. See CLAUDE.md §7 step 7.
        """
        raise NotImplementedError("Implement ExportConfig.validate")

    def to_redacted_dict(self) -> dict[str, object]:
        """Return a dict suitable for logging — token redacted.

        TODO: implement.
        """
        raise NotImplementedError("Implement ExportConfig.to_redacted_dict")
