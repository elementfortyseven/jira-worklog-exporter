"""Command-line interface for the worklog exporter.

The CLI is the headless / scripted counterpart to the GUI; both consume the
same :class:`jwe.config.ExportConfig` via :mod:`jwe.service`.

Exit codes (PRD §11):
    0  success
    1  authentication error
    2  validation error
    3  API error
    4  cancelled by user (Ctrl-C)
    5  permission / scope error
    6  unknown error
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import threading
import traceback
from datetime import date, datetime
from pathlib import Path

from tqdm import tqdm

import jwe.service as service
from jwe.api.auth import AuthHeaderStyle, AuthMode
from jwe.config import ColumnProfile, ExportConfig
from jwe.exporter import ExportProgress, ExportResult

logger = logging.getLogger(__name__)

_EXIT_SUCCESS = 0
_EXIT_AUTH_ERROR = 1
_EXIT_VALIDATION_ERROR = 2
_EXIT_API_ERROR = 3
_EXIT_CANCELLED = 4
_EXIT_PERMISSION_ERROR = 5
_EXIT_UNKNOWN_ERROR = 6


# ---------------------------------------------------------------------------
# Argument helpers
# ---------------------------------------------------------------------------


def _parse_date(value: str) -> date:
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"invalid date {value!r} — expected YYYY-MM-DD"
        ) from exc


def _read_users_file(path: str) -> list[str]:
    """Read account IDs from a file; skip blank lines and # comments."""
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    return [
        line.strip()
        for line in lines
        if line.strip() and not line.strip().startswith("#")
    ]


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    """Build the top-level argument parser with *export* and *discover-cloud-id* subcommands."""
    parser = argparse.ArgumentParser(
        prog="jwe-cli",
        description="Export Jira Cloud worklogs of selected users to CSV.",
    )
    parser.add_argument("--version", action="version", version="jwe-cli 0.1.0")

    sub = parser.add_subparsers(dest="command", metavar="COMMAND")

    # ------------------------------------------------------------------ export
    ep = sub.add_parser("export", help="Export worklogs to CSV.")

    ep.add_argument(
        "--auth-mode",
        dest="auth_mode",
        choices=["service-account", "user-token"],
        default=None,
        metavar="MODE",
        help="Authentication mode: service-account (default) or user-token.",
    )

    # Service Account fields
    ep.add_argument("--cloud-id", dest="cloud_id", default=None, metavar="UUID")
    ep.add_argument(
        "--service-account-email",
        dest="service_account_email",
        default=None,
        metavar="EMAIL",
    )
    ep.add_argument(
        "--auth-header",
        dest="auth_header",
        choices=["basic", "bearer"],
        default=None,
        help="Authorization header style for Service Account mode (default: basic).",
    )

    # User Token fields
    ep.add_argument("--site-url", dest="site_url", default=None, metavar="URL")
    ep.add_argument("--email", dest="email", default=None, metavar="EMAIL")

    # Token — handled manually so main() returns a clean int exit code
    ep.add_argument(
        "--token",
        dest="token",
        default=None,
        metavar="VALUE",
        help="API token value (plaintext). Prefer --token-env.",
    )
    ep.add_argument(
        "--token-env",
        dest="token_env",
        default=None,
        metavar="VARNAME",
        help="Name of env var holding the API token (default: JWE_API_TOKEN).",
    )

    # Filter
    ep.add_argument(
        "--users",
        dest="users",
        default=None,
        metavar="ID,...",
        help="Comma-separated Jira accountIds.",
    )
    ep.add_argument(
        "--users-file",
        dest="users_file",
        default=None,
        metavar="PATH",
        help="File with one accountId per line.",
    )
    ep.add_argument(
        "--from",
        dest="from_date",
        type=_parse_date,
        default=None,
        metavar="YYYY-MM-DD",
    )
    ep.add_argument(
        "--to",
        dest="to_date",
        type=_parse_date,
        default=None,
        metavar="YYYY-MM-DD",
    )
    ep.add_argument(
        "--projects",
        dest="projects",
        default=None,
        metavar="KEY,...",
        help="Comma-separated project keys (optional).",
    )

    # Output
    ep.add_argument("--output-dir", dest="output_dir", default=None, metavar="PATH")
    ep.add_argument(
        "--columns",
        dest="columns",
        choices=["minimal", "standard", "full"],
        default=None,
    )
    ep.add_argument(
        "--delimiter",
        dest="delimiter",
        choices=[",", ";"],
        default=None,
    )

    # Behaviour
    ep.add_argument(
        "--api-version",
        dest="api_version",
        type=int,
        choices=[2, 3],
        default=None,
    )
    ep.add_argument("--verbose", action="store_true", default=False)
    ep.add_argument("--dry-run", dest="dry_run", action="store_true", default=False)

    # -------------------------------------------- discover-cloud-id
    dcp = sub.add_parser(
        "discover-cloud-id",
        help="Print the cloud ID for a Jira Cloud site and exit.",
    )
    dcp.add_argument("site_url", metavar="SITE_URL")

    return parser


# ---------------------------------------------------------------------------
# Config assembly
# ---------------------------------------------------------------------------


def _setup_logging(verbose: bool) -> None:
    logging.basicConfig(
        stream=sys.stderr,
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )


def _apply_args_to_config(args: argparse.Namespace, config: ExportConfig) -> None:
    """Override *config* fields with CLI values, overwriting env-var defaults.

    Raises:
        ValueError: on mutually exclusive flag conflicts or unreadable users-file.
    """
    if args.token is not None and args.token_env is not None:
        raise ValueError("use either --token or --token-env, not both")
    if args.users is not None and args.users_file is not None:
        raise ValueError("use either --users or --users-file, not both")

    if args.auth_mode is not None:
        config.auth_mode = AuthMode(args.auth_mode)
    if args.cloud_id is not None:
        config.cloud_id = args.cloud_id
    if args.service_account_email is not None:
        config.service_account_email = args.service_account_email
    if args.auth_header is not None:
        config.auth_header = AuthHeaderStyle(args.auth_header)
    if args.site_url is not None:
        config.site_url = args.site_url
    if args.email is not None:
        config.email = args.email

    # Token resolution
    if args.token is not None:
        config.api_token = args.token
    elif args.token_env is not None:
        config.api_token = os.environ.get(str(args.token_env), "")

    # Users
    if args.users is not None:
        config.user_account_ids = [u.strip() for u in str(args.users).split(",") if u.strip()]
    elif args.users_file is not None:
        try:
            config.user_account_ids = _read_users_file(str(args.users_file))
        except OSError as exc:
            raise ValueError(f"cannot read users-file: {exc}") from exc

    if args.from_date is not None:
        config.from_date = args.from_date
    if args.to_date is not None:
        config.to_date = args.to_date
    if args.projects is not None:
        config.project_keys = [k.strip() for k in str(args.projects).split(",") if k.strip()]
    if args.output_dir is not None:
        config.output_dir = Path(str(args.output_dir))
    if args.columns is not None:
        config.column_profile = ColumnProfile(args.columns)
    if args.delimiter is not None:
        config.delimiter = str(args.delimiter)
    if args.api_version is not None:
        config.api_version = int(args.api_version)

    config.verbose = bool(args.verbose)
    config.dry_run = bool(args.dry_run)


# ---------------------------------------------------------------------------
# Subcommand handlers
# ---------------------------------------------------------------------------


def _cmd_export(args: argparse.Namespace) -> int:
    _setup_logging(bool(args.verbose))

    config = service.config_from_env()
    try:
        _apply_args_to_config(args, config)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return _EXIT_VALIDATION_ERROR

    try:
        config.validate()
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return _EXIT_VALIDATION_ERROR

    try:
        user = service.test_connection(config)
        print(
            f"Authenticated as: {user.display_name} (accountId: {user.account_id})",
            file=sys.stderr,
        )
    except service.AuthenticationError as exc:
        print(f"error: authentication failed — {exc}", file=sys.stderr)
        return _EXIT_AUTH_ERROR
    except service.JiraPermissionError as exc:
        print(f"error: permission denied — {exc}", file=sys.stderr)
        return _EXIT_PERMISSION_ERROR
    except service.JiraApiError as exc:
        print(f"error: API error — {exc}", file=sys.stderr)
        return _EXIT_API_ERROR

    cancel_event = threading.Event()
    last_progress: ExportProgress | None = None
    result: ExportResult | None = None
    interrupted = False

    gen = service.run_export(config, cancel_event)
    try:
        with tqdm(desc="Exporting", unit=" issues", file=sys.stderr, dynamic_ncols=True) as bar:
            last_issues = 0
            for event in gen:
                if isinstance(event, ExportProgress):
                    last_progress = event
                    delta = event.issues_seen - last_issues
                    if delta > 0:
                        bar.update(delta)
                        last_issues = event.issues_seen
                    bar.set_postfix(worklogs=event.worklogs_written)
                elif isinstance(event, ExportResult):
                    result = event
    except KeyboardInterrupt:
        interrupted = True
        cancel_event.set()
        # Drain the generator so the exporter can yield its final ExportResult
        # after observing cancel_event. This ensures the partial CSV is flushed
        # and the partial counts are reported correctly.
        for event in gen:
            if isinstance(event, ExportProgress):
                last_progress = event
            elif isinstance(event, ExportResult):
                result = event
    except service.JiraApiError as exc:
        print(f"\nerror: {exc}", file=sys.stderr)
        logger.debug("API error details", exc_info=True)
        return _EXIT_API_ERROR
    except Exception as exc:
        print(f"\nerror: unexpected error — {exc}", file=sys.stderr)
        if bool(args.verbose):
            traceback.print_exc(file=sys.stderr)
        logger.debug("Unexpected error", exc_info=True)
        return _EXIT_UNKNOWN_ERROR

    _print_summary(result, last_progress, interrupted)
    return _EXIT_CANCELLED if interrupted else _EXIT_SUCCESS


def _print_summary(
    result: ExportResult | None,
    last_progress: ExportProgress | None,
    interrupted: bool,
) -> None:
    tag = "(cancelled) " if interrupted else ""
    if result is not None:
        secs = result.total_time_spent_seconds
        h, rem = divmod(secs, 3600)
        m = rem // 60
        print(
            f"\nExport {tag}complete: "
            f"{result.issues_seen} issues, {result.worklogs_written} worklogs, "
            f"{h}h {m}m total time spent"
        )
        if result.output_path:
            print(f"Output: {result.output_path}")
    elif last_progress is not None:
        print(
            f"\nPartial result: "
            f"{last_progress.issues_seen} issues, "
            f"{last_progress.worklogs_written} worklogs processed"
        )


def _cmd_discover_cloud_id(args: argparse.Namespace) -> int:
    try:
        info = service.discover_cloud_id(str(args.site_url))
        print(info.cloud_id)
        return _EXIT_SUCCESS
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return _EXIT_VALIDATION_ERROR
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return _EXIT_API_ERROR


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    """CLI entry point. Returns an exit code per PRD §11."""
    parser = build_parser()
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])

    if args.command == "export":
        return _cmd_export(args)
    if args.command == "discover-cloud-id":
        return _cmd_discover_cloud_id(args)

    parser.print_help(sys.stderr)
    return _EXIT_VALIDATION_ERROR


if __name__ == "__main__":
    raise SystemExit(main())
