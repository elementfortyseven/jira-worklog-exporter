"""Tests for jwe.i18n."""
from __future__ import annotations

from pathlib import Path

import pytest

from jwe.i18n import DEFAULT_LANG, DIAGNOSTICS, STRINGS, diag, t


def test_default_lang_is_en() -> None:
    assert DEFAULT_LANG == "en"


def test_en_returns_english_content() -> None:
    assert "Authentication" in t("section.auth.title", "en")


def test_de_returns_german_content() -> None:
    assert "Authentifizierung" in t("section.auth.title", "de")


def test_de_differs_from_en() -> None:
    assert t("section.auth.title", "de") != t("section.auth.title", "en")


def test_format_substitution_en() -> None:
    result = diag("error.api_failed", detail=403)
    assert "403" in result


def test_format_substitution_de() -> None:
    result = t("auth.status.connected", "de", display_name="Max", email="max@de")
    assert "Max" in result


def test_key_without_placeholder_no_error() -> None:
    # section.auth.title contains no {…} tokens; must not crash when called without kwargs.
    assert t("section.auth.title", "de") == "Authentifizierung"


def test_no_kwargs_returns_raw_template() -> None:
    raw = t("summary.complete", "en")
    assert "{issues_seen}" in raw


def test_unknown_lang_falls_back_to_en() -> None:
    assert t("section.auth.title", "fr") == t("section.auth.title", "en")


def test_unknown_key_raises_keyerror() -> None:
    with pytest.raises(KeyError) as exc_info:
        t("nonexistent.key")
    assert "nonexistent.key" in str(exc_info.value)


def test_key_parity_en_de() -> None:
    """Both language tables must have identical key sets -- prevents drift."""
    assert set(STRINGS["en"].keys()) == set(STRINGS["de"].keys())


@pytest.mark.parametrize("key", sorted(STRINGS["en"].keys()))
def test_all_keys_present_in_de(key: str) -> None:
    assert key in STRINGS["de"], f"Key {key!r} missing in 'de'"


# -- New 6a tests: verify every namespace resolves in both languages ----------


@pytest.mark.parametrize("lang", ["en", "de"])
@pytest.mark.parametrize("key", [
    "app.title",
    "section.auth.title",
    "section.auth.subtitle",
    "section.filter.title",
    "section.filter.subtitle",
    "section.output.title",
    "section.output.subtitle",
    "section.user_search.title",
    "section.users.subtitle",
])
def test_section_keys_resolve(key: str, lang: str) -> None:
    result = t(key, lang)
    assert isinstance(result, str) and result


@pytest.mark.parametrize("lang", ["en", "de"])
@pytest.mark.parametrize("key", [
    "auth.radio.service_account",
    "auth.radio.user_token",
    "auth.sa.label.site_url",
    "auth.sa.label.cloud_id",
    "auth.sa.label.email",
    "auth.sa.label.token",
    "auth.sa.label.auth_header",
    "auth.sa.discovery_url.placeholder",
    "auth.sa.cloud_id.placeholder",
    "auth.sa.email.placeholder",
    "auth.sa.token.placeholder",
    "auth.user.label.site_url",
    "auth.user.label.email",
    "auth.user.label.token",
    "auth.user.site_url.placeholder",
    "auth.user.email.placeholder",
    "auth.user.token.placeholder",
    "auth.btn.discover_cloud_id",
    "auth.btn.test_connection",
    "auth.checkbox.save_token",
    "auth.status.testing",
])
def test_auth_keys_resolve(key: str, lang: str) -> None:
    result = t(key, lang)
    assert isinstance(result, str) and result


@pytest.mark.parametrize("lang", ["en", "de"])
def test_auth_status_connected_resolves(lang: str) -> None:
    result = t("auth.status.connected", lang, display_name="Test User", email="test@example.com")
    assert "Test User" in result


@pytest.mark.parametrize("lang", ["en", "de"])
def test_auth_status_cloud_id_found_resolves(lang: str) -> None:
    result = t("auth.status.cloud_id_found", lang, cloud_id="abc-123")
    assert "abc-123" in result


def test_auth_status_discovery_failed_resolves() -> None:
    result = diag("auth.status.discovery_failed", message="timeout")
    assert "timeout" in result


@pytest.mark.parametrize("lang", ["en", "de"])
@pytest.mark.parametrize("key", [
    "filter.label.from",
    "filter.label.to",
    "filter.label.projects",
    "filter.project_keys.placeholder",
])
def test_filter_keys_resolve(key: str, lang: str) -> None:
    result = t(key, lang)
    assert isinstance(result, str) and result


@pytest.mark.parametrize("lang", ["en", "de"])
@pytest.mark.parametrize("key", [
    "output.label.output_dir",
    "output.label.delimiter",
    "output.label.profile",
    "output.label.api_version",
    "output.btn.browse",
    "output.delimiter.comma",
    "output.delimiter.semicolon",
    "output.browse_dialog.title",
])
def test_output_keys_resolve(key: str, lang: str) -> None:
    result = t(key, lang)
    assert isinstance(result, str) and result


@pytest.mark.parametrize("lang", ["en", "de"])
@pytest.mark.parametrize("key", [
    "user_search.search.placeholder",
    "user_search.btn.add_one",
    "user_search.btn.add_all",
    "user_search.btn.rem_one",
    "user_search.btn.rem_all",
    "user_search.status.searching",
])
def test_user_search_keys_resolve(key: str, lang: str) -> None:
    result = t(key, lang)
    assert isinstance(result, str) and result


@pytest.mark.parametrize("lang", ["en", "de"])
@pytest.mark.parametrize("key", [
    "status.btn.export",
    "status.btn.cancel",
    "status.btn.open_csv",
    "status.btn.open_folder",
    "status.label.ready",
    "status.label.not_ready",
])
def test_status_keys_resolve(key: str, lang: str) -> None:
    result = t(key, lang)
    assert isinstance(result, str) and result


@pytest.mark.parametrize("lang", ["en", "de"])
def test_status_counter_issues_resolves(lang: str) -> None:
    result = t("status.counter.issues_n", lang, n=42)
    assert "42" in result


@pytest.mark.parametrize("lang", ["en", "de"])
def test_status_counter_worklogs_resolves(lang: str) -> None:
    result = t("status.counter.worklogs_n", lang, n=7)
    assert "7" in result


def test_status_log_export_complete_resolves() -> None:
    result = diag("status.log.export_complete", path="/out/file.csv")
    assert "/out/file.csv" in result


def test_status_log_error_resolves() -> None:
    result = diag("status.log.error", message="something went wrong")
    assert "something went wrong" in result


@pytest.mark.parametrize("lang", ["en", "de"])
@pytest.mark.parametrize("key", [
    "dialog.close_during_export.title",
    "dialog.close_during_export.text",
])
def test_dialog_keys_resolve(key: str, lang: str) -> None:
    result = t(key, lang)
    assert isinstance(result, str) and result


@pytest.mark.parametrize("key", [
    "error.unexpected",
    "error.generic",
])
def test_new_error_keys_resolve(key: str) -> None:
    result = diag(key, detail="oops")
    assert "oops" in result


@pytest.mark.parametrize("lang", ["en", "de"])
def test_summary_authenticated_as_resolves(lang: str) -> None:
    result = t("summary.authenticated_as", lang, display_name="Jane", account_id="abc123")
    assert "Jane" in result
    assert "abc123" in result


# -- Diagnostics channel -------------------------------------------------------


def test_no_diagnostics_key_in_strings() -> None:
    """No key may live in both DIAGNOSTICS and STRINGS (no double-home)."""
    overlap = set(DIAGNOSTICS.keys()) & set(STRINGS["en"].keys())
    assert overlap == set(), f"Keys in both dicts: {overlap}"


@pytest.mark.parametrize("key", sorted(DIAGNOSTICS.keys()))
def test_diag_key_resolves(key: str) -> None:
    result = diag(key)
    assert isinstance(result, str) and result


def test_diag_format_substitution() -> None:
    result = diag("error.api_failed", detail="forbidden")
    assert "forbidden" in result


def test_diag_unknown_key_raises_keyerror() -> None:
    with pytest.raises(KeyError) as exc_info:
        diag("nonexistent.diagnostic.key")
    assert "nonexistent.diagnostic.key" in str(exc_info.value)


def test_diag_is_english_only() -> None:
    """diag() always returns English text regardless of locale."""
    result = diag("error.auth_failed", detail="test")
    assert "Authentication failed" in result
    assert "Authentifizierung" not in result


# -- Placeholder coverage (guards against future param-name drift) ------------


@pytest.mark.parametrize("lang", ["en", "de"])
@pytest.mark.parametrize("key, kwargs", [
    ("progress.exporting", {"current": 5, "total": 20}),
    ("progress.partial_result", {"issues_seen": 3, "worklogs_written": 7}),
    ("summary.complete", {"issues_seen": 10, "worklogs_written": 50, "h": 2, "m": 30}),
    ("summary.cancelled", {"issues_seen": 5, "worklogs_written": 20}),
    ("summary.output_path", {"path": "/tmp/out.csv"}),
    ("summary.authenticated_as", {"display_name": "Alice", "account_id": "acc-1"}),
    ("auth.status.connected", {"display_name": "Alice", "email": "alice@example.com"}),
    ("auth.status.cloud_id_found", {"cloud_id": "abc-123-uuid"}),
    ("status.counter.issues_n", {"n": 42}),
    ("status.counter.worklogs_n", {"n": 7}),
])
def test_strings_placeholder_formatting(key: str, kwargs: dict[str, object], lang: str) -> None:
    """t() with the documented kwargs must not raise KeyError or IndexError."""
    result = t(key, lang, **kwargs)
    assert isinstance(result, str) and result


@pytest.mark.parametrize("key, kwargs", [
    ("error.auth_failed", {"detail": "401 Unauthorized"}),
    ("error.permission_denied", {"detail": "403 Forbidden"}),
    ("error.api_failed", {"detail": "500 Server Error"}),
    ("error.validation", {"detail": "missing field"}),
    ("error.unexpected", {"detail": "NullPointerException"}),
    ("error.generic", {"detail": "something failed"}),
    ("auth.status.discovery_failed", {"message": "timeout"}),
    ("status.log.error", {"message": "something went wrong"}),
    ("status.log.export_complete", {"path": "/out/file.csv"}),
])
def test_diagnostics_placeholder_formatting(key: str, kwargs: dict[str, object]) -> None:
    """diag() with the documented kwargs must not raise KeyError or IndexError."""
    result = diag(key, **kwargs)
    assert isinstance(result, str) and result


# -- Marker-grep gate (JWE-2 acceptance criterion) ----------------------------


def test_no_i18n_markers_remain_in_src() -> None:
    """Zero # i18n: markers must remain in src/ — regressions are caught in CI."""
    src_root = Path(__file__).resolve().parents[1] / "src"
    matches = [
        f"{f}:{lineno + 1}: {line.rstrip()}"
        for f in sorted(src_root.rglob("*.py"))
        for lineno, line in enumerate(f.read_text(encoding="utf-8").splitlines())
        if "# i18n:" in line
    ]
    assert matches == [], "Unreplaced # i18n: markers found:\n" + "\n".join(matches)
