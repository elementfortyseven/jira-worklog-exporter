"""Dependency-free i18n for de/en UI strings.

Two string sources:

- ``STRINGS`` + :func:`t`: Localized presentation strings (GUI chrome, labels,
  placeholders, buttons, dialogs, progress, summaries).  Both ``en`` and ``de``
  entries; parity-tested.

- ``DIAGNOSTICS`` + :func:`diag`: English-only.  Used for log-panel lines and
  error/failure messages so that logs are grep-able and troubleshooting stays
  single-language regardless of the selected locale.

Usage::

    from jwe.i18n import diag, t
    print(t("section.auth.title", lang))
    print(diag("error.auth_failed", detail=msg))
"""

from __future__ import annotations

DEFAULT_LANG: str = "en"

STRINGS: dict[str, dict[str, str]] = {
    "en": {
        # ---------------------------------------------------------------- progress.*
        "progress.exporting": "Exporting worklogs ({current}/{total})...",
        "progress.partial_result": "Partial result: {issues_seen} issues, {worklogs_written} worklogs processed",
        # ----------------------------------------------------------------- summary.*
        "summary.complete": "Export complete: {issues_seen} issues, {worklogs_written} worklogs, {h}h {m}m total time spent",
        "summary.cancelled": "Export cancelled: {issues_seen} issues, {worklogs_written} worklogs written before cancellation",
        "summary.output_path": "Output file: {path}",
        "summary.authenticated_as": "Authenticated as: {display_name} (accountId: {account_id})",
        # ------------------------------------------------------------------ status.* (generic)
        "status.connecting": "Connecting...",
        "status.ready": "Ready",
        "status.exporting": "Exporting...",
        "status.cancelled": "Cancelled",
        "status.done": "Done",
        # ------------------------------------------------------------------- app.*
        "app.title": "Jira Worklog Exporter",
        # --------------------------------------------------------------- section.*
        "section.auth.title": "Authentication",
        "section.auth.subtitle": "Service account or personal token",
        "section.filter.title": "Date & Project Filter",
        "section.filter.subtitle": "Date range and project scope",
        "section.output.title": "Output",
        "section.output.subtitle": "File format and destination",
        "section.user_search.title": "Users",
        "section.users.subtitle": "Search and select Jira users",
        # ----------------------------------------------------------------- auth.*
        "auth.radio.service_account": "Service Account",
        "auth.radio.user_token": "Personal API Token",
        # SA labels
        "auth.sa.label.site_url": "Site URL",
        "auth.sa.label.cloud_id": "Cloud ID",
        "auth.sa.label.email": "Email",
        "auth.sa.label.token": "API Token",
        "auth.sa.label.auth_header": "Auth Header",
        # SA placeholders
        "auth.sa.discovery_url.placeholder": "https://your-company.atlassian.net",
        "auth.sa.cloud_id.placeholder": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
        "auth.sa.email.placeholder": "bot@serviceaccount.atlassian.com",
        "auth.sa.token.placeholder": "API token with required scopes",
        # User-token labels
        "auth.user.label.site_url": "Site URL",
        "auth.user.label.email": "Email",
        "auth.user.label.token": "API Token",
        # User-token placeholders
        "auth.user.site_url.placeholder": "https://your-company.atlassian.net",
        "auth.user.email.placeholder": "you@example.com",
        "auth.user.token.placeholder": "Personal API token",
        # Auth buttons & controls
        "auth.btn.discover_cloud_id": "Discover",
        "auth.btn.test_connection": "Test Connection",
        "auth.checkbox.save_token": "Save token to keyring",
        # Auth status messages (presentation -- localized)
        "auth.status.testing": "Testing...",
        "auth.status.connected": "Connected as {display_name} ({email})",
        "auth.status.cloud_id_found": "Cloud ID found: {cloud_id}",
        # ---------------------------------------------------------------- filter.*
        "filter.label.from": "From",
        "filter.label.to": "To",
        "filter.label.projects": "Projects",
        "filter.project_keys.placeholder": "PROJ, SUPP (optional)",
        # ---------------------------------------------------------------- output.*
        "output.label.output_dir": "Output Dir",
        "output.label.delimiter": "Delimiter",
        "output.label.profile": "Profile",
        "output.label.api_version": "API Version",
        "output.btn.browse": "Browse...",
        "output.delimiter.comma": ", (Comma)",
        "output.delimiter.semicolon": "; (Semicolon)",
        "output.browse_dialog.title": "Select output directory",
        # ------------------------------------------------------------- user_search.*
        "user_search.search.placeholder": "Search users...",
        "user_search.btn.add_one": ">",
        "user_search.btn.add_all": ">>",
        "user_search.btn.rem_one": "<",
        "user_search.btn.rem_all": "<<",
        "user_search.status.searching": "Searching...",
        # ----------------------------------------------------------------- status.*
        "status.btn.export": "Start Export",
        "status.btn.cancel": "Cancel",
        "status.btn.open_csv": "Open CSV",
        "status.btn.open_folder": "Open Folder",
        "status.label.ready": "Ready to export",
        "status.label.not_ready": "Fill in required fields",
        "status.counter.issues_n": "Issues: {n}",
        "status.counter.worklogs_n": "Worklogs: {n}",
        # ----------------------------------------------------------------- dialog.*
        "dialog.close_during_export.title": "Export running",
        "dialog.close_during_export.text": "Export is running. Cancel and close?",
    },
    "de": {
        # ---------------------------------------------------------------- progress.*
        "progress.exporting": "Worklogs werden exportiert ({current}/{total})...",
        "progress.partial_result": "Teilergebnis: {issues_seen} Vorgänge, {worklogs_written} Worklogs verarbeitet",
        # ----------------------------------------------------------------- summary.*
        "summary.complete": "Export abgeschlossen: {issues_seen} Vorgänge, {worklogs_written} Worklogs, {h}Std. {m}Min. Gesamtzeit",
        "summary.cancelled": "Export abgebrochen: {issues_seen} Vorgänge, {worklogs_written} Worklogs vor Abbruch geschrieben",
        "summary.output_path": "Ausgabedatei: {path}",
        "summary.authenticated_as": "Authentifiziert als: {display_name} (accountId: {account_id})",
        # ------------------------------------------------------------------ status.* (generic)
        "status.connecting": "Verbindung wird hergestellt...",
        "status.ready": "Bereit",
        "status.exporting": "Export läuft...",
        "status.cancelled": "Abgebrochen",
        "status.done": "Fertig",
        # ------------------------------------------------------------------- app.*
        "app.title": "Jira Worklog Exporter",
        # --------------------------------------------------------------- section.*
        "section.auth.title": "Authentifizierung",
        "section.auth.subtitle": "Service-Account oder persoenlicher Token",
        "section.filter.title": "Datum & Projektfilter",
        "section.filter.subtitle": "Zeitraum und Projektbereich",
        "section.output.title": "Ausgabe",
        "section.output.subtitle": "Dateiformat und Speicherort",
        "section.user_search.title": "Benutzer",
        "section.users.subtitle": "Jira-Benutzer suchen und auswaehlen",
        # ----------------------------------------------------------------- auth.*
        "auth.radio.service_account": "Service Account",
        "auth.radio.user_token": "Persönlicher API-Token",
        # SA labels
        "auth.sa.label.site_url": "Site-URL",
        "auth.sa.label.cloud_id": "Cloud-ID",
        "auth.sa.label.email": "E-Mail",
        "auth.sa.label.token": "API-Token",
        "auth.sa.label.auth_header": "Auth-Header",
        # SA placeholders
        "auth.sa.discovery_url.placeholder": "https://ihre-firma.atlassian.net",
        "auth.sa.cloud_id.placeholder": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
        "auth.sa.email.placeholder": "bot@serviceaccount.atlassian.com",
        "auth.sa.token.placeholder": "API-Token mit erforderlichen Scopes",
        # User-token labels
        "auth.user.label.site_url": "Site-URL",
        "auth.user.label.email": "E-Mail",
        "auth.user.label.token": "API-Token",
        # User-token placeholders
        "auth.user.site_url.placeholder": "https://ihre-firma.atlassian.net",
        "auth.user.email.placeholder": "sie@beispiel.de",
        "auth.user.token.placeholder": "Persönlicher API-Token",
        # Auth buttons & controls
        "auth.btn.discover_cloud_id": "Ermitteln",
        "auth.btn.test_connection": "Verbindung testen",
        "auth.checkbox.save_token": "Token im Schlüsselbund speichern",
        # Auth status messages (presentation -- localized)
        "auth.status.testing": "Wird getestet...",
        "auth.status.connected": "Verbunden als {display_name} ({email})",
        "auth.status.cloud_id_found": "Cloud-ID gefunden: {cloud_id}",
        # ---------------------------------------------------------------- filter.*
        "filter.label.from": "Von",
        "filter.label.to": "Bis",
        "filter.label.projects": "Projekte",
        "filter.project_keys.placeholder": "PROJ, SUPP (optional)",
        # ---------------------------------------------------------------- output.*
        "output.label.output_dir": "Ausgabeverzeichnis",
        "output.label.delimiter": "Trennzeichen",
        "output.label.profile": "Profil",
        "output.label.api_version": "API-Version",
        "output.btn.browse": "Durchsuchen...",
        "output.delimiter.comma": ", (Komma)",
        "output.delimiter.semicolon": "; (Semikolon)",
        "output.browse_dialog.title": "Ausgabeverzeichnis auswählen",
        # ------------------------------------------------------------- user_search.*
        "user_search.search.placeholder": "Benutzer suchen...",
        "user_search.btn.add_one": ">",
        "user_search.btn.add_all": ">>",
        "user_search.btn.rem_one": "<",
        "user_search.btn.rem_all": "<<",
        "user_search.status.searching": "Suche läuft...",
        # ----------------------------------------------------------------- status.*
        "status.btn.export": "Export starten",
        "status.btn.cancel": "Abbrechen",
        "status.btn.open_csv": "CSV öffnen",
        "status.btn.open_folder": "Ordner öffnen",
        "status.label.ready": "Bereit zum Export",
        "status.label.not_ready": "Pflichtfelder ausfüllen",
        "status.counter.issues_n": "Vorgänge: {n}",
        "status.counter.worklogs_n": "Worklogs: {n}",
        # ----------------------------------------------------------------- dialog.*
        "dialog.close_during_export.title": "Export läuft",
        "dialog.close_during_export.text": "Export läuft. Abbrechen und schließen?",
    },
}

# English-only strings: log-panel lines and error/failure messages.
# These are shared by GUI and CLI so logs stay grep-able across locales.
# Use diag() to look them up -- there is no lang parameter.
DIAGNOSTICS: dict[str, str] = {
    # errors / failures
    "error.auth_failed": "Authentication failed: {detail}",
    "error.permission_denied": "Permission denied: {detail}",
    "error.api_failed": "API request failed: {detail}",
    "error.validation": "Validation error: {detail}",
    "error.unexpected": "Unexpected error: {detail}",
    "error.generic": "Error: {detail}",
    "auth.status.discovery_failed": "Discovery failed: {message}",
    "auth.keyring.unavailable": "Keyring unavailable",
    # GUI activity-log lines (log panel is always English)
    "status.log.error": "Error: {message}",
    "status.log.export_complete": "Export complete. Output: {path}",
    "status.log.dry_run_complete": "Dry run complete.",
    "status.log.cancelling": "Cancelling...",
    "status.log.cancelled": "Export cancelled.",
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


def diag(key: str, **kwargs: object) -> str:
    """Return the English-only diagnostic string for *key*.

    Raises :exc:`KeyError` if *key* is absent from :data:`DIAGNOSTICS`.
    """
    template = DIAGNOSTICS.get(key)
    if template is None:
        raise KeyError(f"Unknown diagnostic key: {key!r}")
    if kwargs:
        return template.format(**kwargs)
    return template
