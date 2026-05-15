"""Dependency-free i18n for de/en UI strings.

Two language tables live inside ``STRINGS`` as module constants keyed by
language code.  All user-facing strings in CLI and GUI must go through
:func:`t` so that language switching works at runtime without hardcoding.

Usage::

    from jwe.i18n import t
    print(t("error.auth_failed", lang, detail=msg))
"""

from __future__ import annotations

DEFAULT_LANG: str = "en"

STRINGS: dict[str, dict[str, str]] = {
    "en": {
        # error.*
        "error.auth_failed": "Authentication failed: {detail}",
        "error.permission_denied": "Permission denied: {detail}",
        "error.api_failed": "API request failed (HTTP {status})",
        "error.validation": "Validation error: {detail}",
        "error.cancelled": "Export cancelled.",
        # progress.*
        "progress.exporting": "Exporting worklogs ({current}/{total})...",
        "progress.partial_result": "Partial result: {count} worklogs exported so far.",
        # summary.*
        "summary.complete": "Export complete: {count} worklogs written.",
        "summary.cancelled": "Export cancelled: {count} worklogs written before cancellation.",
        "summary.output_path": "Output file: {path}",
        # label.*
        "label.auth_mode": "Authentication mode",
        "label.cloud_id": "Cloud ID",
        "label.site_url": "Site URL",
        "label.service_account_email": "Service account email",
        "label.email": "Email",
        "label.users": "Users",
        "label.from_date": "From date",
        "label.to_date": "To date",
        "label.projects": "Projects",
        "label.output_dir": "Output directory",
        "label.columns": "Columns",
        "label.delimiter": "Delimiter",
        "label.api_token": "API token",
        # button.*
        "button.test_connection": "Test connection",
        "button.start_export": "Start export",
        "button.cancel": "Cancel",
        "button.search_users": "Search users",
        "button.save_token": "Save token",
        "button.browse": "Browse",
        # status.*
        "status.connecting": "Connecting...",
        "status.ready": "Ready",
        "status.exporting": "Exporting...",
        "status.cancelled": "Cancelled",
        "status.done": "Done",
    },
    "de": {
        # error.*
        "error.auth_failed": "Authentifizierung fehlgeschlagen: {detail}",
        "error.permission_denied": "Zugriff verweigert: {detail}",
        "error.api_failed": "API-Anfrage fehlgeschlagen (HTTP {status})",
        "error.validation": "Validierungsfehler: {detail}",
        "error.cancelled": "Export abgebrochen.",
        # progress.*
        "progress.exporting": "Worklogs werden exportiert ({current}/{total})...",
        "progress.partial_result": "Teilergebnis: {count} Worklogs bisher exportiert.",
        # summary.*
        "summary.complete": "Export abgeschlossen: {count} Worklogs geschrieben.",
        "summary.cancelled": "Export abgebrochen: {count} Worklogs vor Abbruch geschrieben.",
        "summary.output_path": "Ausgabedatei: {path}",
        # label.*
        "label.auth_mode": "Authentifizierungsmodus",
        "label.cloud_id": "Cloud-ID",
        "label.site_url": "Site-URL",
        "label.service_account_email": "Service-Account-E-Mail",
        "label.email": "E-Mail",
        "label.users": "Benutzer",
        "label.from_date": "Von Datum",
        "label.to_date": "Bis Datum",
        "label.projects": "Projekte",
        "label.output_dir": "Ausgabeverzeichnis",
        "label.columns": "Spalten",
        "label.delimiter": "Trennzeichen",
        "label.api_token": "API-Token",
        # button.*
        "button.test_connection": "Verbindung testen",
        "button.start_export": "Export starten",
        "button.cancel": "Abbrechen",
        "button.search_users": "Benutzer suchen",
        "button.save_token": "Token speichern",
        "button.browse": "Durchsuchen",
        # status.*
        "status.connecting": "Verbindung wird hergestellt...",
        "status.ready": "Bereit",
        "status.exporting": "Export läuft...",
        "status.cancelled": "Abgebrochen",
        "status.done": "Fertig",
    },
}


def t(key: str, lang: str = DEFAULT_LANG, **kwargs: object) -> str:
    """Return the translated string for *key* in *lang*.

    Falls back to ``en`` for unknown languages.  Raises :exc:`KeyError` if
    *key* is absent from both the requested language table and English.
    """
    lang_table = STRINGS.get(lang, STRINGS[DEFAULT_LANG])
    template = lang_table.get(key)
    if template is None:
        en_table = STRINGS[DEFAULT_LANG]
        template = en_table.get(key)
        if template is None:
            raise KeyError(f"Unknown i18n key: {key!r}")
    if kwargs:
        return template.format(**kwargs)
    return template
