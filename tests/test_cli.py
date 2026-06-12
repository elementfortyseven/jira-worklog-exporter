"""Tests for jwe.cli."""

from __future__ import annotations

import subprocess
import sys
from datetime import date
from pathlib import Path
from unittest import mock

import pytest

import jwe.service as service
from jwe.api.client import AuthenticationError, JiraApiError, JiraPermissionError
from jwe.api.tenant_info import TenantInfo
from jwe.api.user import User
from jwe.cli import build_parser, main
from jwe.exporter import ExportProgress, ExportResult

# ---------------------------------------------------------------------------
# Constants / helpers
# ---------------------------------------------------------------------------

_CLOUD_ID = "1a11d016-8984-4c3e-b9ab-142dd06acb1b"
_SA_EMAIL = "bot@serviceaccount.atlassian.com"
_SITE_URL = "https://acme.atlassian.net"
_SA_USER = User(account_id="abc123", display_name="Jira Bot", email=_SA_EMAIL, active=True)


def _base_export_args(tmp_path: Path) -> list[str]:
    """Minimal valid CLI args for service-account export."""
    return [
        "export",
        "--cloud-id",
        _CLOUD_ID,
        "--service-account-email",
        _SA_EMAIL,
        "--token",
        "ATATT3xFfGF0dummy",
        "--users",
        "user-001",
        "--from",
        "2026-04-01",
        "--to",
        "2026-04-30",
        "--output-dir",
        str(tmp_path),
    ]


def _noop_run_export(config, cancel_event=None):  # type: ignore[no-untyped-def]
    yield ExportProgress(issues_seen=0, worklogs_written=0)
    yield ExportResult(
        issues_seen=0, worklogs_written=0, total_time_spent_seconds=0, output_path=None
    )


# ---------------------------------------------------------------------------
# build_parser — shape tests
# ---------------------------------------------------------------------------


class TestBuildParser:
    def test_export_all_flags(self) -> None:
        args = build_parser().parse_args(
            [
                "export",
                "--auth-mode",
                "user-token",
                "--site-url",
                _SITE_URL,
                "--email",
                "user@example.com",
                "--token",
                "TOK",
                "--users",
                "u1,u2",
                "--from",
                "2026-01-01",
                "--to",
                "2026-01-31",
                "--projects",
                "PROJ,SUPP",
                "--output-dir",
                "/tmp",
                "--columns",
                "full",
                "--delimiter",
                ";",
                "--api-version",
                "2",
                "--verbose",
                "--dry-run",
            ]
        )
        assert args.auth_mode == "user-token"
        assert args.from_date == date(2026, 1, 1)
        assert args.to_date == date(2026, 1, 31)
        assert args.columns == "full"
        assert args.delimiter == ";"
        assert args.api_version == 2
        assert args.verbose is True
        assert args.dry_run is True

    def test_discover_cloud_id_positional(self) -> None:
        args = build_parser().parse_args(["discover-cloud-id", _SITE_URL])
        assert args.command == "discover-cloud-id"
        assert args.site_url == _SITE_URL

    def test_no_subcommand_returns_nonzero(self) -> None:
        assert main([]) != 0

    def test_invalid_date_format_exits(self) -> None:
        with pytest.raises(SystemExit):
            build_parser().parse_args(["export", "--from", "01-04-2026"])

    def test_invalid_columns_choice_exits(self) -> None:
        with pytest.raises(SystemExit):
            build_parser().parse_args(["export", "--columns", "wrong"])

    def test_gui_subcommand_removed(self) -> None:
        with pytest.raises(SystemExit) as exc:
            main(["gui"])
        assert exc.value.code == 2


# ---------------------------------------------------------------------------
# Qt-free import guard (subprocess: must not load PySide6 / shiboken6)
# ---------------------------------------------------------------------------


def test_cli_import_graph_is_qt_free() -> None:
    code = (
        "import jwe.cli, sys; "
        "assert 'PySide6' not in sys.modules and 'shiboken6' not in sys.modules"
    )
    subprocess.run([sys.executable, "-c", code], check=True)


# ---------------------------------------------------------------------------
# Validation errors (exit 2)
# ---------------------------------------------------------------------------


class TestValidationErrors:
    def test_token_and_token_env_mutual_exclusion(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        code = main([*_base_export_args(tmp_path), "--token-env", "MY_VAR"])
        assert code == 2
        assert "token" in capsys.readouterr().err.lower()

    def test_users_and_users_file_mutual_exclusion(self, tmp_path: Path) -> None:
        users_file = tmp_path / "u.txt"
        users_file.write_text("user-001\n")
        args = [
            "export",
            "--cloud-id",
            _CLOUD_ID,
            "--service-account-email",
            _SA_EMAIL,
            "--token",
            "TOK",
            "--users",
            "user-001",
            "--users-file",
            str(users_file),
            "--from",
            "2026-04-01",
            "--to",
            "2026-04-30",
            "--output-dir",
            str(tmp_path),
        ]
        assert main(args) == 2

    def test_missing_required_fields_exits_2(self, tmp_path: Path) -> None:
        code = main(
            [
                "export",
                "--cloud-id",
                _CLOUD_ID,
                "--service-account-email",
                _SA_EMAIL,
                "--token",
                "TOK",
                "--output-dir",
                str(tmp_path),
            ]
        )
        assert code == 2

    def test_users_file_not_found_exits_2(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        code = main(
            [
                "export",
                "--cloud-id",
                _CLOUD_ID,
                "--service-account-email",
                _SA_EMAIL,
                "--token",
                "TOK",
                "--users-file",
                str(tmp_path / "nonexistent.txt"),
                "--from",
                "2026-04-01",
                "--to",
                "2026-04-30",
                "--output-dir",
                str(tmp_path),
            ]
        )
        assert code == 2
        assert "users-file" in capsys.readouterr().err

    def test_users_file_parsed_and_comments_stripped(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        users_file = tmp_path / "users.txt"
        users_file.write_text("user-001\n# comment\nuser-002\n\n")

        monkeypatch.setattr(service, "test_connection", lambda c: _SA_USER)
        monkeypatch.setattr(service, "run_export", _noop_run_export)

        code = main(
            [
                "export",
                "--cloud-id",
                _CLOUD_ID,
                "--service-account-email",
                _SA_EMAIL,
                "--token",
                "ATATT3xFfGF0dummy",
                "--users-file",
                str(users_file),
                "--from",
                "2026-04-01",
                "--to",
                "2026-04-30",
                "--output-dir",
                str(tmp_path),
            ]
        )
        assert code == 0


# ---------------------------------------------------------------------------
# Authentication / API errors (exit 1, 3, 5)
# ---------------------------------------------------------------------------


class TestAuthErrors:
    def test_authentication_error_exits_1(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            service, "test_connection", mock.Mock(side_effect=AuthenticationError("401"))
        )
        code = main(_base_export_args(tmp_path))
        assert code == 1
        assert "authentication" in capsys.readouterr().err.lower()

    def test_permission_error_exits_5(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            service, "test_connection", mock.Mock(side_effect=JiraPermissionError("403"))
        )
        assert main(_base_export_args(tmp_path)) == 5

    def test_api_error_on_connection_exits_3(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(service, "test_connection", mock.Mock(side_effect=JiraApiError("500")))
        assert main(_base_export_args(tmp_path)) == 3


# ---------------------------------------------------------------------------
# Happy path (exit 0)
# ---------------------------------------------------------------------------


class TestHappyPath:
    def test_export_success_exits_0(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        monkeypatch.setattr(service, "test_connection", lambda c: _SA_USER)
        monkeypatch.setattr(service, "run_export", _noop_run_export)

        assert main(_base_export_args(tmp_path)) == 0
        out = capsys.readouterr().out
        assert "0 issues" in out
        assert "0 worklogs" in out

    def test_output_path_printed_on_success(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        expected = str(tmp_path / "result.csv")

        def run(config, cancel_event=None):  # type: ignore[no-untyped-def]
            yield ExportProgress(issues_seen=1, worklogs_written=2)
            yield ExportResult(
                issues_seen=1,
                worklogs_written=2,
                total_time_spent_seconds=0,
                output_path=expected,
            )

        monkeypatch.setattr(service, "test_connection", lambda c: _SA_USER)
        monkeypatch.setattr(service, "run_export", run)

        assert main(_base_export_args(tmp_path)) == 0
        assert expected in capsys.readouterr().out

    def test_dry_run_exits_0(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(service, "test_connection", lambda c: _SA_USER)
        monkeypatch.setattr(service, "run_export", _noop_run_export)
        assert main([*_base_export_args(tmp_path), "--dry-run"]) == 0


# ---------------------------------------------------------------------------
# KeyboardInterrupt drain loop
# ---------------------------------------------------------------------------


class TestKeyboardInterruptDrainLoop:
    def test_ki_exits_4_and_partial_summary_printed(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """KI during export: drain loop resumes generator; exit 4, counts in summary."""
        progress = ExportProgress(issues_seen=3, worklogs_written=7)
        final = ExportResult(
            issues_seen=3,
            worklogs_written=7,
            total_time_spent_seconds=1800,
            output_path=None,
        )

        def fake_run_export(config, cancel_event=None):  # type: ignore[no-untyped-def]
            yield progress
            # drain loop resumes here after cancel_event is set
            yield final

        monkeypatch.setattr(service, "test_connection", lambda c: _SA_USER)
        monkeypatch.setattr(service, "run_export", fake_run_export)

        # Raise KI from bar.set_postfix: generator stays suspended at yield,
        # so the drain loop can resume it and collect the ExportResult.
        mock_bar = mock.MagicMock()
        mock_bar.__enter__ = mock.Mock(return_value=mock_bar)
        mock_bar.__exit__ = mock.Mock(return_value=False)
        ki_raised = False

        def _raise_ki_once(**kwargs: object) -> None:
            nonlocal ki_raised
            if not ki_raised:
                ki_raised = True
                raise KeyboardInterrupt

        mock_bar.set_postfix.side_effect = _raise_ki_once

        with mock.patch("jwe.cli.tqdm", return_value=mock_bar):
            code = main(_base_export_args(tmp_path))

        assert code == 4
        out = capsys.readouterr().out
        assert "3 issues" in out
        assert "7 worklogs" in out


# ---------------------------------------------------------------------------
# discover-cloud-id
# ---------------------------------------------------------------------------


class TestDiscoverCloudId:
    def test_success_prints_cloud_id_exits_0(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        monkeypatch.setattr(
            service, "discover_cloud_id", lambda url: TenantInfo(cloud_id=_CLOUD_ID)
        )
        assert main(["discover-cloud-id", _SITE_URL]) == 0
        assert _CLOUD_ID in capsys.readouterr().out

    def test_value_error_exits_2(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            service, "discover_cloud_id", mock.Mock(side_effect=ValueError("bad url"))
        )
        assert main(["discover-cloud-id", "not-a-url"]) == 2

    def test_generic_exception_exits_3(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            service, "discover_cloud_id", mock.Mock(side_effect=Exception("connection error"))
        )
        assert main(["discover-cloud-id", _SITE_URL]) == 3
