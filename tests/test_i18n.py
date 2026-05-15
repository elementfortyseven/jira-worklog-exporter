"""Tests for jwe.i18n."""
from __future__ import annotations

import pytest

from jwe.i18n import DEFAULT_LANG, STRINGS, t


def test_default_lang_is_en() -> None:
    assert DEFAULT_LANG == "en"


def test_en_returns_english_content() -> None:
    assert "Authentication failed" in t("error.auth_failed", "en")


def test_de_returns_german_content() -> None:
    assert "Authentifizierung fehlgeschlagen" in t("error.auth_failed", "de")


def test_de_differs_from_en() -> None:
    assert t("error.auth_failed", "de") != t("error.auth_failed", "en")


def test_format_substitution_en() -> None:
    result = t("error.api_failed", "en", status=403)
    assert "403" in result


def test_format_substitution_de() -> None:
    assert "500" in t("error.api_failed", "de", status=500)


def test_label_without_placeholder_no_error() -> None:
    # Cloud-ID contains no {…} tokens; must not crash when called without kwargs.
    assert t("label.cloud_id", "de") == "Cloud-ID"


def test_no_kwargs_returns_raw_template() -> None:
    raw = t("error.auth_failed", "en")
    assert "{detail}" in raw


def test_unknown_lang_falls_back_to_en() -> None:
    assert t("error.auth_failed", "fr") == t("error.auth_failed", "en")


def test_unknown_key_raises_keyerror() -> None:
    with pytest.raises(KeyError) as exc_info:
        t("nonexistent.key")
    assert "nonexistent.key" in str(exc_info.value)


def test_key_parity_en_de() -> None:
    """Both language tables must have identical key sets — prevents drift."""
    assert set(STRINGS["en"].keys()) == set(STRINGS["de"].keys())


@pytest.mark.parametrize("key", sorted(STRINGS["en"].keys()))
def test_all_keys_present_in_de(key: str) -> None:
    assert key in STRINGS["de"], f"Key {key!r} missing in 'de'"
