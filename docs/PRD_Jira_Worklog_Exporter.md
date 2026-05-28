# Product Requirements Document
## Jira Cloud Worklog Exporter

| Feld | Wert |
|---|---|
| Dokument-Version | 1.2 |
| Status | Draft |
| Datum | 2026-05-28 |
| Autor | Martin |
| Zielplattform | Windows 11 (primär), plattformunabhängig (Python) |
| Zielsystem | Jira Cloud (REST API v3, eine Site einer Organisation) |
| Änderungen ggü. 1.0 | Service-Account-Authentifizierung als bevorzugter Modus ergänzt; Gateway-URL `api.atlassian.com/ex/jira/{cloudId}` etabliert; Cloud-ID-Discovery; Scope- und Permission-Layering dokumentiert; Anhang A „Setup-Anleitung für Org-Admins" hinzugefügt. |
| Änderungen ggü. 1.1 | Python-Mindestversion auf 3.12 angehoben (3.11 aus CI entfernt); GUI-Tests nur auf Windows verifiziert, Linux/Mac als CLI-Plattform unterstützt. |

---

## 1. Zusammenfassung

Der **Jira Cloud Worklog Exporter** ist ein kleines, eigenständiges Werkzeug zum Export von Arbeitszeit-Buchungen (Worklogs) aus einer Jira-Cloud-Site (eine Site innerhalb einer Atlassian-Organisation) nach CSV. Der Export erfolgt nutzerspezifisch (ein oder mehrere Benutzer) und optional eingeschränkt auf einen Zeitraum und/oder ein Projekt. Die Ausgabe ist eine CSV-Datei mit einer Zeile pro Worklog-Eintrag und enthält die Spalten **Projekt, Vorgangsschlüssel, Summary, Benutzer, Time Spent, Work Description**.

Das Tool authentifiziert sich entweder über ein **Atlassian-Service-Account-Token (bevorzugt)** oder über ein klassisches personenbezogenes API-Token (Fallback). Im Service-Account-Modus läuft der Verkehr über das Atlassian-Platform-Gateway `https://api.atlassian.com/ex/jira/{cloudId}`, im klassischen Modus direkt gegen die Site-URL.

Das Tool wird als Python-Skript mit optionalem PySide6-GUI ausgeliefert und kann via PyInstaller plus GitHub-Actions-Workflow als signierte Windows-Executable gebaut werden — analog zum bestehenden „Jira Project Leads Exporter".

---

## 2. Hintergrund & Motivation

In Jira Cloud sind Worklogs zwar pro Vorgang sichtbar, aber für eine pro-Benutzer-Auswertung über mehrere Projekte hinweg fehlt eine native, gut filterbare Export-Funktion. Vorhandene Bordmittel (Tempo o. Ä.) sind kostenpflichtige Marketplace-Apps. Für interne Auswertungen, Reports an Stakeholder oder Stundenabrechnungen wird ein leichtgewichtiges Werkzeug gebraucht, das:

- ohne zusätzliche Marketplace-Lizenz auskommt,
- mit Standard-Jira-Cloud-API-Token authentifiziert,
- reproduzierbare CSV-Outputs erzeugt, die direkt in Excel/Power BI/Pandas weiterverarbeitet werden können.

---

## 3. Ziele & Nicht-Ziele

### 3.1 Ziele (In Scope)

1. Worklogs eines oder mehrerer Benutzer aus **einer Jira-Cloud-Site** (innerhalb einer Atlassian-Organisation) exportieren.
2. Filterung nach Datumsbereich (Worklog-Datum, nicht Vorgangs-Datum).
3. Optionale Einschränkung auf bestimmte Projekte (Projekt-Schlüssel).
4. CSV-Ausgabe mit fester Spaltenstruktur (siehe §8).
5. UTF-8-Kodierung mit BOM, damit Excel die CSV korrekt öffnet.
6. Bereitstellung als CLI-Skript **und** als optionales PySide6-GUI (cross-platform).
7. **Zwei Authentifizierungsmodi:**
   - **(A) Service Account** mit scopes-basiertem API-Token, Auth über `https://api.atlassian.com/ex/jira/{cloudId}` (bevorzugt — überlebt Mitarbeiter-Wechsel, klar abgegrenzte Scopes).
   - **(B) Personenbezogenes API-Token** (legacy/scoped), Auth direkt gegen `https://<site>.atlassian.net` (Fallback für Setups ohne Org-Admin-Zugriff oder mit < 5 verfügbaren Service Accounts).
8. Sichere Handhabung des API-Tokens (kein Klartext-Persistieren by default).
9. Robustes Verhalten bei API-Ratenlimits (HTTP 429) und Pagination.
10. Build-Pipeline für eine Standalone-Windows-Executable über GitHub Actions.

### 3.2 Nicht-Ziele (Out of Scope, v1)

- Schreibender Zugriff auf Jira (Worklogs anlegen, ändern, löschen).
- Integration mit Tempo Timesheets oder anderen Marketplace-Apps.
- Auswertung/Aggregation innerhalb des Tools (Summen, Gruppierung, Diagramme) — Aufgabe der nachgelagerten Tools wie Excel/Power BI.
- **xlsx-Export** (CSV reicht laut Anforderung; potenziell v1.1).
- Unterstützung für Jira Data Center / Server (kann in v2 ergänzt werden).
- **Mehrere Sites einer Organisation in einer Session** — das Skript spricht pro Lauf genau eine Site an.
- **OAuth 2.0 Client Credentials Flow** für Service Accounts (zwar inzwischen verfügbar, aber komplexer in Konfiguration und Token-Refresh; angedacht für v2.0).
- **OAuth 2.0 (3LO)** für interaktive User-Anmeldung — v1 verwendet API-Token-basierte Verfahren.
- Automatischer Versand (Mail, SharePoint-Upload o. Ä.).
- Profile/Filter-Sets speichern und laden (v1.1).

---

## 4. Zielgruppe & Personas

**Primäre Zielgruppe:** Jira-Administrator:innen, Team-Leads, Projekt-Manager und Controller, die regelmäßig Stundenauswertungen pro Mitarbeiter:in erstellen müssen.

**Persona „Jira-Admin Martin":** Verwaltet eine Jira-Cloud-Instanz, hat Site-Admin-Rechte oder zumindest Browse-Project- und View-Worklog-Rechte für relevante Projekte. Arbeitet auf Windows 11, ist mit Python und CLI vertraut, möchte aber Stakeholdern eine Doppel-Klick-Lösung an die Hand geben können.

**Persona „Team-Lead Tina":** Möchte einmal im Monat die Stunden ihres Teams exportieren, ohne sich JQL ausdenken zu müssen. Braucht ein GUI mit Eingabefeldern für Zeitraum und Benutzerliste.

---

## 5. Use Cases

| ID | Use Case | Akteur |
|---|---|---|
| UC-01 | Monatlicher Stundenexport für einen einzelnen Mitarbeiter, alle Projekte | Team-Lead |
| UC-02 | Quartalsexport für mehrere Mitarbeiter eines Teams, alle Projekte | Team-Lead, Controller |
| UC-03 | Projekt-spezifischer Export (z. B. nur für Kundenprojekt X) für Abrechnung | Projekt-Manager |
| UC-04 | Headless-Export aus Skript / Scheduler heraus (CLI, ohne GUI) | Admin / Automatisierung |
| UC-05 | Ad-hoc-Export für Audit-Zwecke (alle Worklogs eines Users im letzten Jahr) | Admin |

---

## 6. Funktionale Anforderungen

### 6.1 Authentifizierung & Verbindung

Das Tool unterstützt zwei Authentifizierungsmodi, die sich in URL-Schema, Auth-Header und benötigten Vorbedingungen unterscheiden.

#### Modus A: Service Account (bevorzugt)

- **FR-01a:** Pflichtparameter: **Cloud ID** (UUID der Site), **Service-Account-Email** (Form `*@serviceaccount.atlassian.com`) und **API-Token**.
- **FR-02a:** Base-URL für alle API-Aufrufe: `https://api.atlassian.com/ex/jira/{cloudId}/rest/api/3/...`
- **FR-03a:** Authentifizierung wahlweise:
  - **Basic Auth** mit `<service-account-email>:<token>` (Default)
  - **Bearer Auth** mit `Authorization: Bearer <token>` (kompatibel mit moderneren Atlassian-Endpoints)
- **FR-04a:** Erforderliche Token-Scopes (mindestens):
  - Klassisch: `read:jira-work`, `read:jira-user`
  - Granular (empfohlen, falls vom Ziel-Tenant unterstützt): `read:issue:jira`, `read:issue-worklog:jira`, `read:user:jira`, `read:project:jira`, `read:jql:jira`
- **FR-05a:** Cloud-ID-Discovery-Helfer: Optional erlaubt das Tool die Eingabe der Site-URL (z. B. `https://acme.atlassian.net`) und ermittelt die Cloud-ID via `GET https://acme.atlassian.net/_edge/tenant_info` (anonymer Endpoint, kein Token nötig). Ergebnis wird im GUI angezeigt und kann mit „Übernehmen" in das Cloud-ID-Feld geschrieben werden.

#### Modus B: Personenbezogenes API-Token (Fallback)

- **FR-01b:** Pflichtparameter: **Site-URL** (Format `https://<tenant>.atlassian.net`), **Email** und **API-Token** (mit oder ohne Scopes).
- **FR-02b:** Base-URL für alle API-Aufrufe: `https://<tenant>.atlassian.net/rest/api/3/...`
- **FR-03b:** Authentifizierung per Basic Auth `<email>:<token>`.
- **FR-04b:** Falls das Token Scopes besitzt, gelten dieselben Scope-Anforderungen wie unter FR-04a.

#### Gemeinsame Anforderungen

- **FR-06:** Beim Start (CLI und GUI) wird die Verbindung über einen leichten Test-Call validiert:
  - Modus A: `GET /rest/api/3/myself` über die Gateway-URL
  - Modus B: `GET /rest/api/3/myself` über die Site-URL
  Die Antwort liefert `accountId` und `displayName` der authentifizierten Identität — bei Service Accounts ist das der Service Account selbst, was als Bestätigung dient.
- **FR-07:** Fehler werden klar gemeldet und vom üblichen 401/403/404 unterschieden (siehe §13). Insbesondere differenziert das Tool zwischen „Auth gescheitert" (Token falsch/abgelaufen) und „Permission gescheitert" (Token gültig, aber Scope/Project-Permission fehlt).
- **FR-08:** Sensible Werte (Token, Email) dürfen aus Umgebungsvariablen gelesen werden. Default-Variablen:
  - `JWE_AUTH_MODE` = `service-account` | `user-token`
  - `JWE_CLOUD_ID` (Modus A)
  - `JWE_SITE_URL` (Modus B)
  - `JWE_EMAIL` (beide)
  - `JWE_API_TOKEN` (beide)
- **FR-09:** Token niemals in Logs, Stack-Traces oder Fehlermeldungen ausgeben.

### 6.2 Service-Account-Voraussetzungen (Pre-Conditions)

Diese Voraussetzungen liegen außerhalb des Tools und müssen vom Org-Admin erfüllt werden, bevor das Tool im Modus A produktiv genutzt werden kann (siehe Anhang A für eine Schritt-für-Schritt-Anleitung):

- **PRE-01:** Service Account ist via `admin.atlassian.com → Directory → Service accounts` angelegt.
- **PRE-02:** Service Account hat **App Access** zu „Jira" (Mitgliedschaft in der entsprechenden App-Access-Gruppe, z. B. `jira-software-users-<site>`).
- **PRE-03:** Service Account ist allen relevanten **Projekten** in der Rolle „Users" (oder einer Rolle mit `View All Worklogs`-Permission) zugeordnet.
- **PRE-04:** API-Token mit den unter FR-04a genannten Scopes ist erstellt.
- **PRE-05:** Cloud ID der Site ist bekannt (über Atlassian Admin oder den Discovery-Endpoint).
- **PRE-06:** Token ist sicher abgelegt (Windows Credential Manager, Vault, CI/CD-Secret-Store o. Ä.).
- **PRE-07:** Token-Ablaufdatum ist im Kalender oder Monitoring vermerkt (max. 365 Tage Gültigkeit, **Scopes können nach Erstellung nicht mehr geändert werden** — bei Rotation muss der Scope-Set neu ausgewählt werden).

### 6.3 Benutzerauswahl

- **FR-10:** Benutzer werden per **accountId** identifiziert (Cloud-Pflicht; `username` ist deprecated).
- **FR-11:** Das Tool bietet eine Benutzersuche an (`GET /rest/api/3/user/search?query=<email-or-name>`), die Treffer mit `displayName`, `emailAddress` (sofern sichtbar) und `accountId` anzeigt.
- **FR-12:** Mehrfachauswahl ist möglich (mindestens ein Benutzer ist Pflicht).
- **FR-13:** Im CLI-Modus akzeptiert das Tool eine kommaseparierte Liste von accountIds **oder** eine Datei mit einer accountId pro Zeile (`--users-file users.txt`).

### 6.4 Filter

- **FR-14:** **Zeitraum** (Pflicht): `from` und `to` als Datum (lokale Zeitzone der Jira-Instanz, ISO-Format `YYYY-MM-DD`). Default-Vorschlag im GUI: aktueller Monat.
- **FR-15:** **Projekt-Filter** (optional): kommaseparierte Liste von Projekt-Keys (z. B. `PROJ,SUPP`). Leer = alle für den User sichtbaren Projekte.
- **FR-16:** Die Kombination der Filter wird als JQL aufgebaut, z. B.
  ```
  worklogAuthor in ("accountId1", "accountId2")
  AND worklogDate >= "2026-04-01"
  AND worklogDate <= "2026-04-30"
  AND project in (PROJ, SUPP)
  ```

### 6.5 Datenabruf

- **FR-17:** Vorgänge werden via `POST /rest/api/3/search/jql` (Enhanced JQL Search) mit obigem JQL und nur den nötigen Feldern (`summary`, `project`, `issuetype`) geholt — gemäß aktueller Cloud-API (der alte `GET /search`-Endpunkt ist deprecated).
- **FR-18:** Pagination wird über den `nextPageToken`-Mechanismus der Enhanced Search korrekt durchlaufen, bis keine weiteren Seiten vorliegen.
- **FR-19:** Für jeden Vorgang werden die Worklogs via `GET /rest/api/3/issue/{issueIdOrKey}/worklog` mit `startedAfter` und `startedBefore` als Unix-Millisekunden geladen, ebenfalls paginiert.
- **FR-20:** Pro abgerufenem Worklog wird geprüft, ob `author.accountId` in der ausgewählten User-Liste enthalten ist; nur passende Worklogs werden in den Output übernommen (zusätzliche client-seitige Filterung als Sicherheitsnetz).
- **FR-21:** Worklog-Kommentare werden im **Atlassian Document Format (ADF)** geliefert. Das Tool flacht ADF zu reinem Text ab (rekursiver ADF→Text-Walker), Zeilenumbrüche und Listen werden sinnvoll erhalten.
- **FR-22:** Optional kann v2 der API verwendet werden (`/rest/api/2/`), die Kommentare als Plain-Text liefert. Konfigurierbares Flag `--api-version 2|3`, Default `3`. *Hinweis:* Im Service-Account-Modus ist die v2-Variante eingeschränkt — viele Tenants akzeptieren nur scoped v3-Calls über das Gateway.

### 6.6 Rate Limiting & Robustheit

- **FR-23:** Das Tool respektiert HTTP 429 mit `Retry-After`-Header und führt automatisches Exponential Backoff (max. 5 Retries) durch.
- **FR-24:** Transiente 5xx-Fehler führen zu Retries (max. 3) mit Backoff.
- **FR-25:** Permanente Fehler (4xx außer 429) brechen den Export ab und werden im Log/UI protokolliert.
- **FR-26:** Ein Abbruch (Strg-C / „Cancel"-Button) ist jederzeit möglich; bereits geschriebene Daten bleiben erhalten (Append-Streaming, siehe §6.7).

### 6.7 CSV-Ausgabe

- **FR-27:** Spalten in fester Reihenfolge (siehe §8).
- **FR-28:** Encoding: **UTF-8 mit BOM** (`utf-8-sig`), Trennzeichen Komma, Quoting `csv.QUOTE_MINIMAL`. Optional konfigurierbar: Semikolon (DE-Excel-Standard) via `--delimiter ";"`.
- **FR-29:** Die Ausgabe wird **streamend** geschrieben (zeilenweise pro Worklog), damit auch sehr große Exporte (> 100k Zeilen) möglich sind, ohne den Speicher zu sprengen.
- **FR-30:** Default-Dateiname: `jira_worklogs_<from>_<to>_<timestamp>.csv` im benutzerdefinierten Output-Verzeichnis (Default: aktuelles Arbeitsverzeichnis bzw. `Documents/`).

### 6.8 Logging

- **FR-31:** Strukturiertes Logging (Python `logging`) mit Levels INFO/WARN/ERROR, optional DEBUG via `--verbose`.
- **FR-32:** Log-Datei neben CSV: `jira_worklogs_<timestamp>.log`. Kein Klartext-Token im Log.
- **FR-33:** GUI zeigt Statusleiste + scrollbares Log-Panel mit den letzten N Einträgen.

### 6.9 Fortschrittsanzeige

- **FR-34:** CLI: Fortschrittsbalken (z. B. `tqdm`) mit „Issues processed / total" und „Worklogs found".
- **FR-35:** GUI: Fortschrittsbalken + numerische Anzeige; Cancel-Button stoppt sauber.

---

## 7. Nicht-funktionale Anforderungen

| Bereich | Anforderung |
|---|---|
| Performance | 10.000 Worklogs in unter 5 Min. (typische Cloud-Latenz, kein Rate-Limiting) |
| Speicher | < 200 MB RAM auch bei 100k+ Zeilen (Streaming-Output) |
| Sicherheit | API-Token wird **nicht** standardmäßig persistiert; keine Tokens in Logs |
| Portabilität | Python 3.12+; Linux/Mac/Windows (CLI); GUI-Tests nur auf Windows verifiziert; PyInstaller-Build für Windows 11 x64 |
| Internationalisierung | UI-Texte auf Englisch und Deutsch, umschaltbar (i18n-fähige String-Tabelle) |
| Lizenz | MIT |
| Abhängigkeiten | extern `requests`, `tqdm`, `PySide6` (GUI-Extra); optional `keyring` |
| Wartbarkeit | Trennung von API-Layer, Domain-Layer (Worklog-Modell) und UI-Layer (CLI/GUI) |

---

## 8. CSV-Spezifikation

| # | Spaltenname | Typ | Quelle | Beispiel |
|---|---|---|---|---|
| 1 | `project_key` | string | `issue.fields.project.key` | `PROJ` |
| 2 | `project_name` | string | `issue.fields.project.name` | `Customer Portal` |
| 3 | `issue_key` | string | `issue.key` | `PROJ-123` |
| 4 | `issue_summary` | string | `issue.fields.summary` | `Login-Bug fixen` |
| 5 | `worklog_author_displayname` | string | `worklog.author.displayName` | `Martin Mustermann` |
| 6 | `worklog_author_account_id` | string | `worklog.author.accountId` | `5b10a2844c...` |
| 7 | `worklog_author_email` | string \| empty | `worklog.author.emailAddress` (kann durch User-Privacy fehlen) | `martin@example.com` |
| 8 | `worklog_started` | ISO-8601 | `worklog.started` | `2026-04-15T09:30:00.000+0200` |
| 9 | `time_spent` | string | `worklog.timeSpent` | `1h 30m` |
| 10 | `time_spent_seconds` | int | `worklog.timeSpentSeconds` | `5400` |
| 11 | `work_description` | string | `worklog.comment` (ADF→Text geflacht) | `Refactoring der Login-Komponente` |
| 12 | `worklog_id` | string | `worklog.id` | `10001` |
| 13 | `worklog_created` | ISO-8601 | `worklog.created` | `2026-04-15T10:00:00.000+0200` |
| 14 | `worklog_updated` | ISO-8601 | `worklog.updated` | `2026-04-15T10:00:00.000+0200` |

> **Hinweis:** Die vom User in der Anfrage geforderten sechs Pflichtspalten sind **#1, #3, #4, #5, #9, #11**. Spalten 2, 6, 7, 8, 10, 12, 13, 14 sind optional und werden über das Flag `--columns minimal|standard|full` gesteuert. Default = `standard`.

---

## 9. Technische Architektur

### 9.1 Tech Stack

- **Sprache:** Python 3.12+
- **HTTP-Client:** `requests` mit `requests.adapters.HTTPAdapter` und `urllib3.util.retry.Retry`. **Bewusste Entscheidung gegen Fertigbibliotheken** wie `atlassian-python-api` oder `jira`: Die meisten dieser Bibliotheken hardcoden die Site-URL `https://<tenant>.atlassian.net` und sind daher mit Service-Account-Tokens nicht kompatibel — diese erfordern zwingend das Platform-Gateway `https://api.atlassian.com/ex/jira/{cloudId}`. Eigener, schlanker Client gibt uns die nötige Flexibilität für beide Auth-Modi.
- **GUI:** `PySide6` (Qt6-Bindings) — **Toolkit-Entscheidung:** Initial war `tkinter` (Standardbibliothek, kein extra Footprint) geplant. Mit Blick auf Cross-Platform-Anforderungen (Windows-first, Mac/Linux nicht ausgeschlossen), die geplante Nutzer-Skalierung (5–15 → ~3 000) und die Anforderung, optisch mit der Atlassian-Cloud-UI mitzuhalten, wurde auf PySide6 gewechselt. PyInstaller unterstützt PySide6; der Build-Footprint ist größer als bei Tkinter.
- **CSV:** `csv` (Standardbibliothek)
- **Progress:** `tqdm` (CLI), `QProgressBar` via PySide6 (GUI)
- **Logging:** `logging` (Standardbibliothek)
- **Optional:** `keyring` für sichere Token-Speicherung im Windows Credential Manager
- **Build:** `pyinstaller --onefile --windowed` für GUI-Variante; `--console` für CLI-Variante. GitHub Actions Workflow auf `windows-latest`.

### 9.2 Modulstruktur

```
jira_worklog_exporter/
├── src/
│   └── jwe/
│       ├── __init__.py
│       ├── __main__.py           # python -m jwe
│       ├── api/
│       │   ├── __init__.py
│       │   ├── client.py         # JiraCloudClient: Auth-Modus-Switch (SA vs User), Retry, Pagination
│       │   ├── auth.py           # AuthStrategy: BasicAuth, BearerAuth, ServiceAccountAuth
│       │   ├── url_builder.py    # Site-URL vs Gateway-URL je nach Auth-Modus
│       │   ├── tenant_info.py    # Cloud-ID-Discovery via /_edge/tenant_info
│       │   ├── search.py         # POST /search/jql Wrapper
│       │   ├── worklog.py        # GET /issue/{key}/worklog Wrapper
│       │   └── user.py           # GET /user/search Wrapper
│       ├── adf.py                # ADF -> Plain Text Konverter
│       ├── exporter.py           # Domain Logic: Filter -> CSV-Stream
│       ├── csv_writer.py         # Streamender CSV-Writer
│       ├── config.py             # ExportConfig dataclass, validate(), build_auth()
│       ├── i18n.py               # de/en Strings
│       ├── service.py            # Service-Layer (CLI und GUI)
│       ├── cli.py                # CLI-Entry-Point (argparse)
│       ├── gui_main.py           # QApplication-Bootstrapper
│       └── gui/                  # PySide6-GUI-Package
│           ├── __init__.py
│           ├── main_window.py    # MainWindow (QMainWindow)
│           ├── widgets/          # auth, filter, output, status, user_search
│           └── workers/          # connection_test, cloud_id_discover, user_search
├── tests/
│   ├── conftest.py
│   ├── fixtures/
│   │   └── adf_samples.json
│   ├── test_adf.py
│   ├── test_auth.py
│   ├── test_cli.py
│   ├── test_client.py
│   ├── test_config.py
│   ├── test_csv_writer.py
│   ├── test_exporter.py
│   ├── test_i18n.py
│   ├── test_search.py
│   ├── test_service.py
│   ├── test_tenant_info.py
│   ├── test_url_builder.py
│   ├── test_user.py
│   ├── test_worklog.py
│   └── gui/                      # pytest-qt GUI-Tests
│       ├── test_auth_widget.py
│       ├── test_filter_widget.py
│       ├── test_main_window.py
│       ├── test_output_widget.py
│       ├── test_status_widget.py
│       └── test_user_search_widget.py
├── .github/workflows/
│   └── build-windows.yml
├── pyproject.toml
├── README.md
└── LICENSE
```

### 9.3 Datenfluss

```
[GUI/CLI Input]
    ↓
[Config + Validation]
    ↓
[JiraCloudClient.connect()  → /myself]
    ↓
[User Resolution (accountIds)]
    ↓
[JQL Build]
    ↓
[Search.iter_issues(jql)]   ←── Pagination via nextPageToken
    ↓                            (yields IssueRef)
[Worklog.iter_worklogs(issueKey, from, to, accountIds)]
    ↓                            (yields Worklog)
[ADF → Plain Text]
    ↓
[CsvWriter.append_row(...)]      ← streamend, flush nach jeder Zeile
    ↓
[Done: Pfad + Statistik]
```

---

## 10. UI-Design (PySide6-GUI)

**Layout (vertikal, Single-Window, ~640×560 px):**

1. **Verbindung** (Group)
   - **Auth-Modus** (Radio-Buttons): „Service Account (empfohlen)" / „Personenbezogenes Token"
   - **Bei Service Account:**
     - Cloud ID (Textfeld) + Button „Aus Site-URL ermitteln" (öffnet kleines Hilfsdialog mit Site-URL-Feld; ruft `/_edge/tenant_info` auf)
     - Service-Account-Email (Textfeld, Placeholder zeigt Format `*@serviceaccount.atlassian.com`)
     - API Token (Password-Feld)
     - Auth-Header (Dropdown): Basic / Bearer (Default Basic)
   - **Bei personenbezogenem Token:**
     - Site-URL (Textfeld, Placeholder `https://acme.atlassian.net`)
     - Email (Textfeld)
     - API Token (Password-Feld)
   - Checkbox „Token im Windows Credential Manager speichern" (nutzt `keyring`; Schlüssel-Name enthält Auth-Modus + Identifier, damit User- und Service-Account-Token getrennt liegen)
   - Button „Verbindung testen" → grünes/rotes Status-Label mit Klartext „Authentifiziert als: <displayName> (accountId: …)"
2. **Benutzer** (Group)
   - Suchfeld + „Suchen"-Button
   - Listbox mit Suchergebnissen (Mehrfachauswahl)
   - Zweite Listbox: ausgewählte Benutzer
3. **Filter** (Group)
   - Datum von / Datum bis (Date-Picker; einfache Entry-Felder mit Validierung reichen v1)
   - Projekt-Keys (kommasepariert, optional)
4. **Ausgabe** (Group)
   - Output-Pfad (Textfeld + „Durchsuchen"-Button)
   - Delimiter-Auswahl (`,` / `;`)
   - Spalten-Profil (`minimal` / `standard` / `full`)
5. **Aktion**
   - Großer Button „Export starten"
   - Fortschrittsbalken + Statuszeile
   - Mini-Log-Panel (read-only, scrollbar, letzte 50 Zeilen)
   - „Cancel"-Button (nur aktiv während Lauf)
   - „CSV öffnen" / „Ordner öffnen" (nach Erfolg)

**Sprachumschalter** oben rechts: 🇩🇪 / 🇬🇧.

---

## 11. CLI-Spezifikation

```
jwe export
  # Auth-Modus
  --auth-mode      service-account            (default; oder: user-token)

  # Modus A: Service Account
  --cloud-id       85b56c8a-891d-...          (Pflicht bei service-account)
  --service-account-email  bot@serviceaccount.atlassian.com
  --auth-header    basic                      (basic|bearer, default basic)

  # Modus B: User Token (statt --cloud-id)
  --site-url       https://acme.atlassian.net (Pflicht bei user-token)
  --email          martin@example.com

  # Token (für beide Modi)
  --token-env      JWE_API_TOKEN              (oder --token <plain>, nicht empfohlen)

  # Filter
  --users          5b10a2844c...,5c11b39556...   (oder --users-file users.txt)
  --from           2026-04-01
  --to             2026-04-30
  --projects       PROJ,SUPP                  (optional)

  # Ausgabe
  --output-dir     ./exports
  --columns        standard                   (minimal|standard|full)
  --delimiter      ","                        (oder ";")

  # Sonstiges
  --api-version    3                          (3|2; bei service-account nur 3 zuverlässig)
  --verbose
  --dry-run                                    (liefert nur Statistik, keine Datei)
  --discover-cloud-id  https://acme.atlassian.net  (Hilfskommando, gibt Cloud ID aus und beendet)
```

Exit-Codes:
- `0` Erfolg
- `1` Auth-Fehler (Token ungültig/abgelaufen)
- `2` Validierungs-Fehler (ungültige Argumente)
- `3` API-Fehler (4xx/5xx, nicht erholbar)
- `4` Abgebrochen vom Benutzer
- `5` Permission-/Scope-Fehler (Token gültig, aber Scope oder Project-Permission fehlt)
- `6` Unbekannter Fehler

---

## 12. Sicherheit

- **SR-01:** API-Token wird im GUI-Passwortfeld maskiert und niemals geloggt.
- **SR-02:** Wenn der Benutzer „Token speichern" wählt, wird das Token via `keyring` im OS-Schlüsselbund (Windows Credential Manager) abgelegt — nicht in einer Klartext-Konfigurationsdatei. Schlüssel-Name enthält Auth-Modus und Identifier, damit User- und Service-Account-Token nicht versehentlich verwechselt werden.
- **SR-03:** Alle HTTP-Aufrufe sind ausschließlich HTTPS; HTTP-Redirects werden nicht akzeptiert.
- **SR-04:** Eingaben (URL, Email, Cloud ID, Projekt-Keys, Datum) werden gegen reguläre Ausdrücke validiert, bevor sie in JQL oder URLs eingebaut werden. Projekt-Keys müssen `^[A-Z][A-Z0-9_]+$` matchen, Cloud IDs `^[0-9a-f-]{36}$`.
- **SR-05:** accountIds werden in JQL-Strings als Quoted Strings eingesetzt; Anführungszeichen in IDs werden escaped.
- **SR-06:** Dependencies werden via `pyproject.toml` gepinnt; Dependabot/Renovate-konform.
- **SR-07:** Der GitHub-Actions-Build erzeugt SHA-256-Hashes der Executable und veröffentlicht sie im Release.
- **SR-08:** **Service-Account-Token-Lifecycle:** Das Tool zeigt beim Connect-Test die verbleibende Token-Laufzeit an, sofern Atlassian das Ablaufdatum im Antwort-Header preisgibt. Bei < 30 Tagen Restlaufzeit erscheint eine deutliche Warnung mit Hinweis auf die Rotations-Pflicht.
- **SR-09:** **Least-Privilege-Empfehlung im README:** Service Accounts sollen ausschließlich Read-Scopes bekommen (`read:jira-work`, `read:jira-user`) — niemals `write:` oder `admin:`. Der Service Account soll nur den Projekten zugeordnet werden, die wirklich exportiert werden.
- **SR-10:** **Trennung Test / Prod:** Empfehlung im README, separate Service Accounts (und damit Tokens) für Test- und Produktivinstanzen anzulegen, um versehentliche Cross-Tenant-Zugriffe auszuschließen.

---

## 13. Fehlerszenarien & UX

| Szenario | Verhalten |
|---|---|
| Falsche URL / DNS-Fehler | Klare Fehlermeldung „Jira-URL nicht erreichbar (DNS)" |
| HTTP 401 (User-Token-Modus) | „Authentifizierung fehlgeschlagen — Email/API-Token prüfen" |
| HTTP 401 (Service-Account-Modus) | „Authentifizierung fehlgeschlagen — Token abgelaufen oder Scopes fehlen. Bitte Token mit den Scopes `read:jira-work`, `read:jira-user` neu erstellen." |
| HTTP 403 auf `/myself` (SA-Modus) | „Service Account hat keinen Jira-App-Access. Bitte Org-Admin bitten, den Account in die Gruppe `jira-software-users-<site>` aufzunehmen." |
| HTTP 403 auf Projekt | Worklogs aus diesem Projekt werden übersprungen, Warnung im Log: „Service Account hat keinen Zugriff auf Projekt X — fehlt vermutlich die Project-Rolle 'Users'." Export läuft weiter |
| HTTP 404 auf Cloud-ID-Pfad | „Cloud ID falsch oder Site existiert nicht. Mit `--discover-cloud-id <site-url>` ermitteln." |
| HTTP 429 | Auto-Retry mit Respekt vor `Retry-After` |
| Leere Ergebnismenge | CSV mit Header ohne Datenzeilen; Hinweis im UI |
| Ungültiges Datum | Validierung vor Export, Hinweis am Feld |
| Kein User ausgewählt | Export-Button bleibt deaktiviert |
| Output-Datei nicht beschreibbar | Fehlermeldung mit Pfad, kein partieller Schreibversuch |
| Ungültige Cloud-ID-Form | UI-seitige Validierung gegen `^[0-9a-f-]{36}$` |

---

## 14. Build & Distribution

- **Repo-Host:** GitHub (privat oder öffentlich, nach Wahl).
- **CI:** `.github/workflows/build-windows.yml` mit Trigger auf Tags `v*`.
  - Schritte: Setup Python 3.12 → `pip install -e .[build]` → `pyinstaller jwe-gui.spec` → `pyinstaller jwe-cli.spec` → SHA-256-Manifest → Upload zu GitHub Release.
- **Artefakte:** `JiraWorklogExporter-GUI.exe`, `jwe-cli.exe`, `SHA256SUMS.txt`.
- **Versionierung:** Semantic Versioning (`MAJOR.MINOR.PATCH`).
- **Code-Signing:** v1 unsigniert; in v2 ggf. mit Sigstore/Self-Hosted-Cert.

---

## 15. Akzeptanzkriterien

| ID | Kriterium |
|---|---|
| AC-01 | Mit gültiger URL, Email und Token wird `/myself` erfolgreich aufgerufen und der Display-Name angezeigt. |
| AC-02 | Bei Auswahl eines Benutzers, einem Datumsbereich von 30 Tagen und keinem Projektfilter werden alle Worklogs dieses Benutzers in den ausgewählten Tagen exportiert. |
| AC-03 | CSV enthält genau die Pflichtspalten Projekt, Issue-Key, Issue-Summary, Benutzer, Time Spent, Work Description und alle Datenzeilen sind vollständig befüllt (außer optionalen Feldern wie Email). |
| AC-04 | CSV öffnet in Excel (DE) ohne Encoding-Fehler bei Umlauten und Sonderzeichen. |
| AC-05 | ADF-Kommentare mit fettem Text, Listen und Erwähnungen werden zu lesbarem Plain Text konvertiert (Listen mit Bindestrich, Erwähnungen als `@DisplayName`). |
| AC-06 | Bei einem simulierten 429-Response retried der Client und schließt den Export erfolgreich ab. |
| AC-07 | Ein 30-Tage-Export über 50.000 Worklogs läuft mit < 200 MB RAM und korrekter Zeilenzahl in der CSV. |
| AC-08 | GitHub-Actions-Workflow baut bei einem Tag-Push erfolgreich beide Executables und hängt sie an das Release. |
| AC-09 | Token-Eingaben erscheinen in keinem Log und keinem Stack-Trace. |
| AC-10 | CLI mit `--dry-run` liefert nur Statistik (Anzahl Issues, Anzahl Worklogs, Summe Sekunden) ohne CSV. |

---

## 16. Risiken & Offene Punkte

| ID | Risiko / Offene Frage | Auswirkung | Mitigation |
|---|---|---|---|
| R-01 | Atlassian deprecated v2 der API; Worklog-Comment-ADF-Parsing wird Pflicht | mittel | ADF-Parser von Anfang an robust; v3 als Default |
| R-02 | User-Email ist durch Privacy-Settings nicht abrufbar | gering | Spalte darf leer sein, kein Abbruch |
| R-03 | JQL-Operator `worklogAuthor` setzt `View All Worklogs`-Permission auf den Projekten voraus | hoch | Im README und in PRE-03 dokumentieren; Fallback: Suche über `assignee` + client-seitige Filterung (deutlich teurer, daher nur Notfall) |
| R-04 | Sehr große Tenants: Pagination kann Stunden dauern | mittel | Streaming-CSV, Cancel-Button, klare Progress-Anzeige |
| R-05 | Datumsfilter `worklogDate` arbeitet in der Zeitzone des aufrufenden Users — kann bei verteilten Teams zu Edge-Cases an Tagesgrenzen führen | gering | Im README dokumentieren; ggf. Option `--timezone` in v2 |
| R-06 | **Service-Account-Token-Rotation:** Tokens haben max. 365 Tage Laufzeit; nach Erstellung können Scopes nicht mehr geändert werden | mittel | Hinweis in der GUI bei < 30 Tagen Restlaufzeit; README-Abschnitt zu Rotations-Workflow; ggf. zwei Tokens parallel halten für nahtlosen Wechsel |
| R-07 | **Service-Account-Limit von 5 pro Org** ohne Atlassian Guard | mittel | Ein einziger Account für alle Read-Only-Auswertungen genügt — eng begründet im README; Fallback auf User-Token-Modus, falls keine SA-Slots frei |
| R-08 | **Drei-Layer-Permission-Matrix** (App Access ∩ Project Role ∩ Token Scope) führt bei Service Accounts häufig zu schwer diagnostizierbaren 401/403 | hoch | Differenzierte Fehlermeldungen (siehe §13); Permission-Helper-Hinweis im README; CLI-Subcommand `jwe doctor` für Diagnose-Run |
| R-09 | Atlassian-Agile-/Software-spezifische Endpoints sind mit Service Accounts teils inkompatibel | gering | Wir nutzen ausschließlich Platform-API (`/rest/api/3`), keine Agile-API. Bei Bedarf in v2 prüfen. |
| R-10 | Atlassian ändert die Service-Account-Mechanik weiter (OAuth Client Credentials, neue Scope-Granularitäten) | mittel | Modulare Auth-Strategy-Architektur; quartalsweiser Review der Atlassian-Roadmap |

**Offene Fragen / Klärungen mit User:**

- ~~Soll v1 bereits einen Excel-(.xlsx)-Export anbieten oder reicht CSV?~~ → **Geklärt: CSV reicht.**
- ~~Soll das Tool mehrere Jira-Cloud-Tenants in einer Session verwalten?~~ → **Geklärt: Nein, eine Site pro Lauf.**
- ~~Wird ein Konfigurationsprofil-Mechanismus benötigt?~~ → **Geklärt: Erst v1.1.**
- **Neu offen:** Liegt die Org-Admin-Berechtigung für die Anlage des Service Accounts vor? Falls nein, ist v1 zwingend mit User-Token-Modus zu starten und der SA-Modus erst nachzulegen.
- **Neu offen:** Sollen Logs den Service-Account-Display-Namen enthalten (Audit-Trail), oder ist das aus Datenschutzsicht problematisch? (Vorschlag: Display-Name OK, Email maskieren.)

---

## 17. Roadmap

| Version | Inhalt |
|---|---|
| v1.0 | Kernfunktionalität laut diesem PRD (CLI + GUI, Windows-Build) |
| v1.1 | Profile (Speichern/Laden von Filtern als JSON), zusätzliche Spaltenprofile, .xlsx-Export |
| v1.2 | Jira-Data-Center-Unterstützung (PAT-Auth) |
| v2.0 | OAuth 2.0 Client Credentials Flow für Service Accounts (kein Long-Lived-Token mehr); OAuth 2.0 (3LO) für interaktive User-Anmeldung; Auswertungs-Dashboard (lokal, kein Server) |

---

## 18. Glossar

- **Worklog:** Einzelne Zeitbuchung an einem Jira-Vorgang (Stunden + optional Kommentar).
- **JQL:** Jira Query Language — Suchsprache für Vorgänge.
- **ADF:** Atlassian Document Format — JSON-basiertes Rich-Text-Format der API v3.
- **accountId:** Eindeutige, nicht-personenbezogene ID eines Jira-Cloud-Users (oder Service Accounts).
- **API-Token:** Token, in `id.atlassian.com` (User) bzw. `admin.atlassian.com → Service accounts` (SA) erzeugt; ersetzt das Passwort bei API-Aufrufen. Cloud-Tokens sind seit Dez. 2024 grundsätzlich befristet (max. 365 Tage).
- **Site:** Eine Jira-/Confluence-Instanz innerhalb einer Atlassian-Organisation, z. B. `acme.atlassian.net`. Eine Organisation kann mehrere Sites haben; dieses Tool spricht pro Lauf genau eine Site an.
- **Cloud ID:** UUID, die eine Site eindeutig identifiziert. Wird für API-Aufrufe über das Platform-Gateway gebraucht.
- **Service Account:** Nicht-personenbezogene Atlassian-Identität, ausschließlich für API-Zugriff. Verbraucht keine Lizenz, kann sich nicht interaktiv einloggen, wird vom Org-Admin verwaltet.
- **Scope:** Berechtigungs-Granularität eines API-Tokens. Bei Service-Account-Tokens und scoped User-Tokens zwingend; bei klassischen (legacy) User-Tokens optional.
- **Platform-Gateway:** `https://api.atlassian.com/ex/jira/{cloudId}/...` — der API-Einstieg für scoped Tokens. Im Gegensatz zum klassischen `https://<site>.atlassian.net/...`.
- **Granular Scopes:** Feinere Scope-Variante (z. B. `read:issue:jira` statt `read:jira-work`). Empfohlen für neue Integrationen.

---

## Anhang A: Setup-Anleitung für den Org-Admin (Service-Account-Modus)

Diese Anleitung beschreibt die einmalige Einrichtung eines Service Accounts für das Tool. Voraussetzung: **Organisation-Admin-Rolle** (nicht nur Site-Admin).

### A.1 Service Account anlegen

1. `https://admin.atlassian.com` öffnen.
2. Falls mehrere Organisationen vorhanden: gewünschte Organisation auswählen.
3. Im linken Menü: **Directory → Service accounts**.
4. **Create service account** klicken.
5. Name: z. B. `jwe-worklog-exporter` (Konvention: Tool-Name + Zweck).
6. Description: Verwendungszweck, verantwortlicher Owner-User, Erstellungsdatum, ggf. Ticket-Referenz.
7. Speichern. Atlassian generiert automatisch eine Email der Form `<id>@serviceaccount.atlassian.com` — diese wird später für Basic Auth gebraucht und sollte notiert werden.

### A.2 App Access vergeben

Der Service Account braucht Zugriff auf das Jira-Produkt:

1. Service Account in der Liste auswählen → **Add to group**.
2. Gruppe `jira-software-users-<site>` (oder die vergleichbare App-Access-Gruppe der Site) hinzufügen.
3. Falls Confluence/JSM später ergänzt werden soll: ebenfalls dort hinzufügen.

### A.3 Project Permissions setzen

Für jedes Projekt, dessen Worklogs exportiert werden sollen:

1. Im Site-UI: Projekt öffnen → **Project settings → People** (oder **Access** in neueren Layouts).
2. Service Account hinzufügen (per Email `<id>@serviceaccount.atlassian.com`).
3. Rolle: **Users** (oder eine projekt-spezifische Rolle, die mindestens `Browse Projects` und `View All Worklogs` erlaubt).
4. **Wichtig:** Ohne `View All Worklogs` greift der JQL-Operator `worklogAuthor` nicht — der Export bleibt leer. Der Permission Helper unter **Project settings → Permissions → Permission Helper** kann das für eine Beispiel-Issue verifizieren.

### A.4 API-Token mit Scopes erstellen

1. Zurück zu `admin.atlassian.com → Directory → Service accounts`.
2. Den eben angelegten Service Account auswählen.
3. **Actions → Create credential → API token**.
4. Name: `jwe-readonly-<datum>` (Konvention: Zweck + Erstellungsdatum, hilft bei Rotation).
5. **Expiration:** maximal 365 Tage. Empfehlung: 90 oder 180 Tage, mit Kalender-Reminder für Rotation.
6. **Scopes auswählen** — mindestens:
   - `read:jira-work` (klassisch) **oder** die granularen Äquivalente:
     - `read:issue:jira`
     - `read:issue-worklog:jira`
     - `read:project:jira`
     - `read:jql:jira`
   - `read:jira-user` (klassisch) **oder** `read:user:jira`
   - **Keine Write- oder Admin-Scopes!**
7. **Create** klicken. Das Token wird **genau einmal** angezeigt — sofort in einen Passwort-Manager oder das CI/CD-Secret-Store kopieren. Atlassian speichert es nicht.

> ⚠️ **Wichtig:** Scopes können nach Token-Erstellung **nicht mehr geändert werden**. Wenn später ein Scope fehlt, muss ein neues Token mit dem gewünschten Scope-Set erstellt werden.

### A.5 Cloud ID ermitteln

Die Cloud ID wird vom Tool für die Gateway-URL gebraucht. Drei Wege:

- **Automatisch:** `jwe export --discover-cloud-id https://acme.atlassian.net` ausführen.
- **Über Browser/curl:** `curl https://acme.atlassian.net/_edge/tenant_info` (anonymer Endpoint, gibt JSON mit `cloudId` zurück).
- **Über Admin-UI:** `admin.atlassian.com → Settings → Sites`. Site auswählen — die Cloud ID ist Bestandteil der URL nach `/s/` (z. B. `1a11d016-8984-4c3e-b9ab-142dd06acb1b`).

### A.6 Verbindung mit dem Tool testen

```bash
# Token in Umgebungsvariable
export JWE_API_TOKEN="..."

# Connect-Test
jwe export \
  --auth-mode service-account \
  --cloud-id 1a11d016-8984-4c3e-b9ab-142dd06acb1b \
  --service-account-email jwe-worklog-exporter@serviceaccount.atlassian.com \
  --token-env JWE_API_TOKEN \
  --dry-run \
  --users <accountId> --from 2026-04-01 --to 2026-04-30
```

Ein erfolgreicher `--dry-run` zeigt: „Authentifiziert als: jwe-worklog-exporter (accountId: …) — Verbindung OK. 0 Issues, 0 Worklogs gefunden im Trockenlauf."

### A.7 Token-Rotation (alle ≤ 365 Tage)

1. Neues Token mit identischem Scope-Set erstellen (Schritt A.4).
2. Neues Token in Secret-Store ablegen, parallel zum alten.
3. Tool / Konsumenten auf neues Token umstellen.
4. Funktion verifizieren.
5. Altes Token in `admin.atlassian.com → Service accounts → <SA> → Actions → View API tokens → Revoke` widerrufen.

### A.8 Cleanup beim Außerbetriebnehmen

1. Alle Tokens des Service Accounts widerrufen.
2. Service Account aus Project-People-Listen entfernen (oder optional belassen, wenn Audit-Historie wichtig ist).
3. Service Account aus App-Access-Gruppen entfernen.
4. Service Account löschen (`admin.atlassian.com → Directory → Service accounts → Delete`).
