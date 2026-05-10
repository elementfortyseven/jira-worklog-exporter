"""Minimal i18n for de/en UI strings.

The dependency-free approach: a dict of string keys to per-language strings.
Add keys as you go; never hardcode user-facing strings outside this module
(except in tests).

TODO (claude code):
1. Build the ``STRINGS`` table as you implement features.
2. Wire :func:`t` into :mod:`cli` and :mod:`gui`.
3. Default language is auto-detected from ``locale.getdefaultlocale()``;
   override via ``--lang de|en`` (CLI) or the GUI language switcher.
"""

from __future__ import annotations

from typing import Literal

Language = Literal["de", "en"]

DEFAULT_LANGUAGE: Language = "de"

STRINGS: dict[str, dict[Language, str]] = {
    "connection.test_ok": {
        "de": "Verbindung OK — authentifiziert als {identity}",
        "en": "Connection OK — authenticated as {identity}",
    },
    "connection.test_fail_auth": {
        "de": "Authentifizierung fehlgeschlagen. Bitte Email/Token prüfen.",
        "en": "Authentication failed. Please check email/token.",
    },
    "connection.test_fail_scopes": {
        "de": (
            "Authentifizierung fehlgeschlagen — Token vorhanden, aber Scopes fehlen. "
            "Token mit den Scopes 'read:jira-work' und 'read:jira-user' neu erstellen."
        ),
        "en": (
            "Authentication failed — token valid but scopes missing. "
            "Recreate the token with scopes 'read:jira-work' and 'read:jira-user'."
        ),
    },
    # TODO: add more keys as the UI/CLI grows.
}


def t(key: str, language: Language = DEFAULT_LANGUAGE, **fmt: object) -> str:
    """Translate a string key to the given language.

    Falls back to English if a key is missing in the requested language,
    and to the literal key if missing in both.
    """
    bundle = STRINGS.get(key)
    if not bundle:
        return key
    template = bundle.get(language) or bundle.get("en") or key
    return template.format(**fmt) if fmt else template
