# Product Requirements Document
## Jira Cloud Worklog Exporter

| Field | Value |
|---|---|
| Document version | 1.2 |
| Status | Draft |
| Date | 2026-05-29 |
| Author | Martin |
| Target platform | Windows 11 (primary), platform-independent (Python) |
| Target system | Jira Cloud (REST API v3, one site of an organisation) |
| Changes vs. 1.0 | Service account authentication added as the preferred mode; gateway URL `api.atlassian.com/ex/jira/{cloudId}` established; cloud ID discovery; scope and permission layering documented; Appendix A "Setup guide for org admins" added. |
| Changes vs. 1.1 | Python minimum version raised to 3.12 (3.11 removed from CI); GUI tests verified on Windows only, Linux/Mac supported as CLI platforms. |

---

## 1. Summary

The **Jira Cloud Worklog Exporter** is a small, self-contained tool for exporting time entries (worklogs) from a Jira Cloud site (one site within an Atlassian organisation) to CSV. The export is user-specific (one or more users) and optionally restricted to a date range and/or a project. The output is a CSV file with one row per worklog entry, containing the columns **project, issue key, summary, user, time spent, work description**.

The tool authenticates either via an **Atlassian service account token (preferred)** or via a classic personal API token (fallback). In service account mode, traffic flows through the Atlassian Platform gateway `https://api.atlassian.com/ex/jira/{cloudId}`; in classic mode it goes directly against the site URL.

The tool ships as a Python script with an optional PySide6 GUI and can be built as a signed Windows executable via PyInstaller plus a GitHub Actions workflow — analogous to the existing "Jira Project Leads Exporter".

---

## 2. Background & Motivation

In Jira Cloud, worklogs are visible per issue, but there is no native, well-filterable export function for per-user evaluation across multiple projects. Available built-in tools (Tempo or similar) are paid marketplace apps. For internal evaluations, reports to stakeholders, or hours billing, a lightweight tool is needed that:

- works without an additional marketplace licence,
- authenticates with a standard Jira Cloud API token,
- produces reproducible CSV outputs that can be processed directly in Excel/Power BI/Pandas.

---

## 3. Goals & Non-Goals

### 3.1 Goals (In Scope)

1. Export worklogs of one or more users from **one Jira Cloud site** (within an Atlassian organisation).
2. Filtering by date range (worklog date, not issue date).
3. Optional restriction to specific projects (project keys).
4. CSV output with a fixed column structure (see §8).
5. UTF-8 encoding with BOM so Excel opens the CSV correctly.
6. Distribution as a CLI script **and** as an optional PySide6 GUI (cross-platform).
7. **Two authentication modes:**
   - **(A) Service Account** with a scopes-based API token, auth via `https://api.atlassian.com/ex/jira/{cloudId}` (preferred — survives employee turnover, clearly bounded scopes).
   - **(B) Personal API token** (legacy/scoped), auth directly against `https://<site>.atlassian.net` (fallback for setups without org admin access or with fewer than 5 available service accounts).
8. Secure handling of the API token (no clear-text persistence by default).
9. Robust behaviour on API rate limits (HTTP 429) and pagination.
10. Build pipeline for a standalone Windows executable via GitHub Actions.

### 3.2 Non-Goals (Out of Scope, v1)

- Write access to Jira (creating, modifying, deleting worklogs).
- Integration with Tempo Timesheets or other marketplace apps.
- Evaluation/aggregation inside the tool (sums, grouping, charts) — task of downstream tools like Excel/Power BI.
- **xlsx export** (CSV is sufficient per requirement; possibly v1.1).
- Support for Jira Data Center / Server (may be added in v2).
- **Multiple sites of an organisation in one session** — the script addresses exactly one site per run.
- **OAuth 2.0 Client Credentials Flow** for service accounts (now available, but more complex in configuration and token refresh; planned for v2.0).
- **OAuth 2.0 (3LO)** for interactive user login — v1 uses API-token-based methods.
- Automatic distribution (mail, SharePoint upload, etc.).
- Saving and loading profiles/filter sets (v1.1).

---

## 4. Target Audience & Personas

**Primary target audience:** Jira administrators, team leads, project managers, and controllers who regularly produce per-employee hours evaluations.

**Persona "Jira admin Jane":** Manages a Jira Cloud instance, has site admin rights or at least Browse Project and View Worklog rights for relevant projects. Works on Windows 11, comfortable with Python and CLI, but wants to give stakeholders a double-click solution.

**Persona "Team lead Joe":** Wants to export his team's hours once a month without having to invent JQL. Needs a GUI with input fields for date range and user list.

---

## 5. Use Cases

| ID | Use Case | Actor |
|---|---|---|
| UC-01 | Monthly hours export for a single employee, all projects | Team lead |
| UC-02 | Quarterly export for several employees of a team, all projects | Team lead, controller |
| UC-03 | Project-specific export (e.g. only for customer project X) for billing | Project manager |
| UC-04 | Headless export from script / scheduler (CLI, no GUI) | Admin / automation |
| UC-05 | Ad-hoc export for audit purposes (all worklogs of a user in the last year) | Admin |

---

## 6. Functional Requirements

### 6.1 Authentication & Connection

The tool supports two authentication modes that differ in URL scheme, auth header, and required preconditions.

#### Mode A: Service Account (preferred)

- **FR-01a:** Required parameters: **Cloud ID** (UUID of the site), **service account email** (format `*@serviceaccount.atlassian.com`), and **API token**.
- **FR-02a:** Base URL for all API calls: `https://api.atlassian.com/ex/jira/{cloudId}/rest/api/3/...`
- **FR-03a:** Authentication choice:
  - **Basic Auth** with `<service-account-email>:<token>` (default)
  - **Bearer Auth** with `Authorization: Bearer <token>` (compatible with more modern Atlassian endpoints)
- **FR-04a:** Required token scopes (minimum):
  - Classic: `read:jira-work`, `read:jira-user`
  - Granular (recommended, if supported by the target tenant): `read:issue:jira`, `read:issue-worklog:jira`, `read:user:jira`, `read:project:jira`, `read:jql:jira`
- **FR-05a:** Cloud ID discovery helper: Optionally the tool accepts the site URL (e.g. `https://acme.atlassian.net`) and determines the cloud ID via `GET https://acme.atlassian.net/_edge/tenant_info` (anonymous endpoint, no token required). The result is shown in the GUI and can be written into the cloud ID field via "Apply".

#### Mode B: Personal API Token (fallback)

- **FR-01b:** Required parameters: **Site URL** (format `https://<tenant>.atlassian.net`), **email**, and **API token** (with or without scopes).
- **FR-02b:** Base URL for all API calls: `https://<tenant>.atlassian.net/rest/api/3/...`
- **FR-03b:** Authentication via Basic Auth `<email>:<token>`.
- **FR-04b:** If the token has scopes, the same scope requirements apply as in FR-04a.

#### Shared Requirements

- **FR-06:** At startup (CLI and GUI), the connection is validated via a lightweight test call:
  - Mode A: `GET /rest/api/3/myself` via the gateway URL
  - Mode B: `GET /rest/api/3/myself` via the site URL
  The response returns `accountId` and `displayName` of the authenticated identity — for service accounts this is the service account itself, which serves as confirmation.
- **FR-07:** Errors are clearly reported and differentiated from the usual 401/403/404 (see §13). In particular, the tool distinguishes between "auth failed" (token wrong/expired) and "permission failed" (token valid, but scope/project permission missing).
- **FR-08:** Sensitive values (token, email) may be read from environment variables. Default variables:
  - `JWE_AUTH_MODE` = `service-account` | `user-token`
  - `JWE_CLOUD_ID` (Mode A)
  - `JWE_SITE_URL` (Mode B)
  - `JWE_EMAIL` (both)
  - `JWE_API_TOKEN` (both)
- **FR-09:** Never output the token in logs, stack traces, or error messages.

### 6.2 Service Account Preconditions

These preconditions are outside the tool and must be met by the org admin before the tool can be used in Mode A in production (see Appendix A for a step-by-step guide):

- **PRE-01:** Service account is created via `admin.atlassian.com → Directory → Service accounts`.
- **PRE-02:** Service account has **app access** to "Jira" (membership in the corresponding app-access group, e.g. `jira-software-users-<site>`).
- **PRE-03:** Service account is assigned to all relevant **projects** in the "Users" role (or a role with `View All Worklogs` permission).
- **PRE-04:** API token with the scopes listed in FR-04a is created.
- **PRE-05:** Cloud ID of the site is known (via Atlassian admin or the discovery endpoint).
- **PRE-06:** Token is securely stored (Windows Credential Manager, vault, CI/CD secret store, etc.).
- **PRE-07:** Token expiry date is noted in calendar or monitoring (max. 365 days validity, **scopes cannot be changed after creation** — on rotation the scope set must be re-selected).

### 6.3 User Selection

- **FR-10:** Users are identified by **accountId** (Cloud requirement; `username` is deprecated).
- **FR-11:** The tool provides a user search (`GET /rest/api/3/user/search?query=<email-or-name>`) that shows hits with `displayName`, `emailAddress` (where visible), and `accountId`.
- **FR-12:** Multi-selection is possible (at least one user is mandatory).
- **FR-13:** In CLI mode, the tool accepts a comma-separated list of accountIds **or** a file with one accountId per line (`--users-file users.txt`).

### 6.4 Filters

- **FR-14:** **Date range** (mandatory): `from` and `to` as date (local timezone of the Jira instance, ISO format `YYYY-MM-DD`). Default suggestion in GUI: current month.
- **FR-15:** **Project filter** (optional): comma-separated list of project keys (e.g. `PROJ,SUPP`). Empty = all projects visible to the user.
- **FR-16:** The combination of filters is built as JQL, e.g.
  ```
  worklogAuthor in ("accountId1", "accountId2")
  AND worklogDate >= "2026-04-01"
  AND worklogDate <= "2026-04-30"
  AND project in (PROJ, SUPP)
  ```

### 6.5 Data Retrieval

- **FR-17:** Issues are fetched via `POST /rest/api/3/search/jql` (Enhanced JQL Search) with the above JQL and only the necessary fields (`summary`, `project`, `issuetype`) — per current Cloud API (the old `GET /search` endpoint is deprecated).
- **FR-18:** Pagination is correctly traversed via the `nextPageToken` mechanism of Enhanced Search, until no further pages remain.
- **FR-19:** For each issue, worklogs are loaded via `GET /rest/api/3/issue/{issueIdOrKey}/worklog` with `startedAfter` and `startedBefore` as Unix milliseconds, also paginated.
- **FR-20:** Per fetched worklog, it is checked whether `author.accountId` is in the selected user list; only matching worklogs are taken into the output (additional client-side filtering as a safety net).
- **FR-21:** Worklog comments are delivered in **Atlassian Document Format (ADF)**. The tool flattens ADF to plain text (recursive ADF→text walker); line breaks and lists are sensibly preserved.
- **FR-22:** Optionally v2 of the API can be used (`/rest/api/2/`) which delivers comments as plain text. Configurable flag `--api-version 2|3`, default `3`. *Note:* In service account mode, the v2 variant is restricted — many tenants only accept scoped v3 calls via the gateway.

### 6.6 Rate Limiting & Robustness

- **FR-23:** The tool respects HTTP 429 with the `Retry-After` header and performs automatic exponential backoff (max. 5 retries).
- **FR-24:** Transient 5xx errors lead to retries (max. 3) with backoff.
- **FR-25:** Permanent errors (4xx except 429) abort the export and are logged in log/UI.
- **FR-26:** Cancellation (Ctrl-C / "Cancel" button) is possible at any time; already written data is preserved (append streaming, see §6.7).

### 6.7 CSV Output

- **FR-27:** Columns in fixed order (see §8).
- **FR-28:** Encoding: **UTF-8 with BOM** (`utf-8-sig`), separator comma, quoting `csv.QUOTE_MINIMAL`. Optionally configurable: semicolon (DE Excel standard) via `--delimiter ";"`.
- **FR-29:** The output is written **streaming** (one row per worklog), so even very large exports (> 100k rows) are possible without exhausting memory.
- **FR-30:** Default filename: `jira_worklogs_<from>_<to>_<timestamp>.csv` in the user-defined output directory (default: current working directory or `Documents/`).

### 6.8 Logging

- **FR-31:** Structured logging (Python `logging`) with levels INFO/WARN/ERROR, optional DEBUG via `--verbose`.
- **FR-32:** Log file next to CSV: `jira_worklogs_<timestamp>.log`. No clear-text token in the log.
- **FR-33:** GUI shows status bar plus scrollable log panel with the last N entries.

### 6.9 Progress Display

- **FR-34:** CLI: progress bar (e.g. `tqdm`) with "issues processed / total" and "worklogs found".
- **FR-35:** GUI: progress bar plus numeric display; cancel button stops cleanly.

---

## 7. Non-Functional Requirements

| Area | Requirement |
|---|---|
| Performance | 10,000 worklogs in under 5 min. (typical Cloud latency, no rate limiting) |
| Memory | < 200 MB RAM even with 100k+ rows (streaming output) |
| Security | API token is **not** persisted by default; no tokens in logs |
| Portability | Python 3.12+; Linux/Mac/Windows (CLI); GUI tests verified on Windows only; PyInstaller build for Windows 11 x64 |
| Internationalisation | UI texts in English and German, switchable (i18n-capable string table) |
| Licence | MIT |
| Dependencies | external `requests`, `tqdm`, `PySide6` (GUI extra); optional `keyring` |
| Maintainability | Separation of API layer, domain layer (worklog model), and UI layer (CLI/GUI) |

---

## 8. CSV Specification

| # | Column name | Type | Source | Example |
|---|---|---|---|---|
| 1 | `project_key` | string | `issue.fields.project.key` | `PROJ` |
| 2 | `project_name` | string | `issue.fields.project.name` | `Customer Portal` |
| 3 | `issue_key` | string | `issue.key` | `PROJ-123` |
| 4 | `issue_summary` | string | `issue.fields.summary` | `Fix login bug` |
| 5 | `worklog_author_displayname` | string | `worklog.author.displayName` | `Jane Doe` |
| 6 | `worklog_author_account_id` | string | `worklog.author.accountId` | `5b10a2844c...` |
| 7 | `worklog_author_email` | string \| empty | `worklog.author.emailAddress` (may be missing due to user privacy) | `jane@example.com` |
| 8 | `worklog_started` | ISO-8601 | `worklog.started` | `2026-04-15T09:30:00.000+0200` |
| 9 | `time_spent` | string | `worklog.timeSpent` | `1h 30m` |
| 10 | `time_spent_seconds` | int | `worklog.timeSpentSeconds` | `5400` |
| 11 | `work_description` | string | `worklog.comment` (ADF flattened to text) | `Refactoring of the login component` |
| 12 | `worklog_id` | string | `worklog.id` | `10001` |
| 13 | `worklog_created` | ISO-8601 | `worklog.created` | `2026-04-15T10:00:00.000+0200` |
| 14 | `worklog_updated` | ISO-8601 | `worklog.updated` | `2026-04-15T10:00:00.000+0200` |

> **Note:** The six required columns from the user's request are **#1, #3, #4, #5, #9, #11**. Columns 2, 6, 7, 8, 10, 12, 13, 14 are optional and controlled via the `--columns minimal|standard|full` flag. Default = `standard`.

---

## 9. Technical Architecture

### 9.1 Tech Stack

- **Language:** Python 3.12+
- **HTTP client:** `requests` with `requests.adapters.HTTPAdapter` and `urllib3.util.retry.Retry`. **Deliberate decision against ready-made libraries** like `atlassian-python-api` or `jira`: most of these libraries hardcode the site URL `https://<tenant>.atlassian.net` and are therefore incompatible with service account tokens — these require the platform gateway `https://api.atlassian.com/ex/jira/{cloudId}`. Our own thin client gives us the flexibility needed for both auth modes.
- **GUI:** `PySide6` (Qt6 bindings) — **toolkit decision:** Initially `tkinter` (standard library, no extra footprint) was planned. With cross-platform requirements in view (Windows first, Mac/Linux not excluded), the planned user scaling (5–15 → ~3,000), and the requirement to match the visual quality of the Atlassian Cloud UI, the choice was switched to PySide6. PyInstaller supports PySide6; the build footprint is larger than with tkinter.
- **CSV:** `csv` (standard library)
- **Progress:** `tqdm` (CLI), `QProgressBar` via PySide6 (GUI)
- **Logging:** `logging` (standard library)
- **Optional:** `keyring` for secure token storage in the Windows Credential Manager
- **Build:** `pyinstaller --onefile --windowed` for the GUI variant; `--console` for the CLI variant. GitHub Actions workflow on `windows-latest`.

### 9.2 Module structure

```
jira_worklog_exporter/
├── src/
│   └── jwe/
│       ├── __init__.py
│       ├── __main__.py           # python -m jwe
│       ├── api/
│       │   ├── __init__.py
│       │   ├── client.py         # JiraCloudClient: auth mode switch (SA vs user), retry, pagination
│       │   ├── auth.py           # AuthStrategy: BasicAuth, BearerAuth, ServiceAccountAuth
│       │   ├── url_builder.py    # Site URL vs gateway URL per auth mode
│       │   ├── tenant_info.py    # Cloud ID discovery via /_edge/tenant_info
│       │   ├── search.py         # POST /search/jql wrapper
│       │   ├── worklog.py        # GET /issue/{key}/worklog wrapper
│       │   └── user.py           # GET /user/search wrapper
│       ├── adf.py                # ADF -> plain text converter
│       ├── exporter.py           # Domain logic: filter -> CSV stream
│       ├── csv_writer.py         # Streaming CSV writer
│       ├── config.py             # ExportConfig dataclass with validate(), to_redacted_dict(), build_auth()
│       ├── i18n.py               # de/en strings
│       ├── service.py            # Service layer (CLI and GUI)
│       ├── cli.py                # CLI entry point (argparse)
│       ├── gui_main.py           # QApplication bootstrapper
│       └── gui/                  # PySide6 GUI package
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
│   └── gui/                      # pytest-qt GUI tests
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

### 9.3 Data flow

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
[Search.iter_issues(jql)]   <-- Pagination via nextPageToken
    ↓                            (yields IssueRef)
[Worklog.iter_worklogs(issueKey, from, to, accountIds)]
    ↓                            (yields Worklog)
[ADF -> plain text]
    ↓
[CsvWriter.append_row(...)]      <- streaming, flush per row
    ↓
[Done: path + statistics]
```

---

## 10. UI Design (PySide6 GUI)

**Layout (vertical, single window, ~640×560 px):**

1. **Connection** (group)
   - **Auth mode** (radio buttons): "Service account (recommended)" / "Personal token"
   - **For service account:**
     - Cloud ID (text field) plus button "Determine from site URL" (opens a small helper dialog with a site URL field; calls `/_edge/tenant_info`)
     - Service account email (text field, placeholder shows format `*@serviceaccount.atlassian.com`)
     - API token (password field)
     - Auth header (dropdown): Basic / Bearer (default Basic)
   - **For personal token:**
     - Site URL (text field, placeholder `https://acme.atlassian.net`)
     - Email (text field)
     - API token (password field)
   - Checkbox "Store token in Windows Credential Manager" (uses `keyring`; key name includes auth mode and identifier so user and service account tokens are kept separate)
   - Button "Test connection" → green/red status label with plain text "Authenticated as: <displayName> (accountId: …)"
2. **Users** (group)
   - Search field plus "Search" button
   - List box with search results (multi-select)
   - Second list box: selected users
3. **Filter** (group)
   - Date from / date to (date picker; simple validated entry fields are sufficient for v1)
   - Project keys (comma-separated, optional)
4. **Output** (group)
   - Output path (text field plus "Browse" button)
   - Delimiter selection (`,` / `;`)
   - Column profile (`minimal` / `standard` / `full`)
5. **Action**
   - Large button "Start export"
   - Progress bar plus status line
   - Mini log panel (read-only, scrollable, last 50 lines)
   - "Cancel" button (only active during a run)
   - "Open CSV" / "Open folder" (after success)

**Language toggle** top right: 🇩🇪 / 🇬🇧.

---

## 11. CLI Specification

```
jwe export
  # Auth mode
  --auth-mode      service-account            (default; or: user-token)

  # Mode A: Service Account
  --cloud-id       85b56c8a-891d-...          (required for service-account)
  --service-account-email  bot@serviceaccount.atlassian.com
  --auth-header    basic                      (basic|bearer, default basic)

  # Mode B: User Token (instead of --cloud-id)
  --site-url       https://acme.atlassian.net (required for user-token)
  --email          jane@example.com

  # Token (for both modes)
  --token-env      JWE_API_TOKEN              (or --token <plain>, not recommended)

  # Filters
  --users          5b10a2844c...,5c11b39556...   (or --users-file users.txt)
  --from           2026-04-01
  --to             2026-04-30
  --projects       PROJ,SUPP                  (optional)

  # Output
  --output-dir     ./exports
  --columns        standard                   (minimal|standard|full)
  --delimiter      ","                        (or ";")

  # Miscellaneous
  --api-version    3                          (3|2; only 3 reliable with service-account)
  --verbose
  --dry-run                                    (only statistics, no file)
  --discover-cloud-id  https://acme.atlassian.net  (helper command, outputs cloud ID and exits)
```

Exit codes:
- `0` Success
- `1` Auth error (token invalid/expired)
- `2` Validation error (invalid arguments)
- `3` API error (4xx/5xx, not recoverable)
- `4` Cancelled by user
- `5` Permission/scope error (token valid, but scope or project permission missing)
- `6` Unknown error

---

## 12. Security

- **SR-01:** API token is masked in the GUI password field and never logged.
- **SR-02:** If the user chooses "Store token", the token is stored via `keyring` in the OS key chain (Windows Credential Manager) — not in a clear-text configuration file. Key name includes auth mode and identifier so user and service account tokens are not accidentally confused.
- **SR-03:** All HTTP calls are exclusively HTTPS; HTTP redirects are not accepted.
- **SR-04:** Inputs (URL, email, cloud ID, project keys, date) are validated against regular expressions before being inserted into JQL or URLs. Project keys must match `^[A-Z][A-Z0-9_]+$`, cloud IDs `^[0-9a-f-]{36}$`.
- **SR-05:** accountIds are inserted into JQL strings as quoted strings; quotation marks within IDs are escaped.
- **SR-06:** Dependencies are pinned via `pyproject.toml`; Dependabot/Renovate-compliant.
- **SR-07:** The GitHub Actions build produces SHA-256 hashes of the executable and publishes them in the release.
- **SR-08:** **Service account token lifecycle:** At the connect test, the tool displays the remaining token lifetime, provided Atlassian exposes the expiry date in the response header. With less than 30 days remaining, a clear warning appears with a hint about the rotation duty.
- **SR-09:** **Least-privilege recommendation in README:** Service accounts should only get read scopes (`read:jira-work`, `read:jira-user`) — never `write:` or `admin:`. The service account should only be assigned to the projects that are actually exported.
- **SR-10:** **Separation of Test / Prod:** Recommendation in README to create separate service accounts (and thus tokens) for test and production instances to rule out accidental cross-tenant access.

---

## 13. Error Scenarios & UX

| Scenario | Behaviour |
|---|---|
| Wrong URL / DNS error | Clear error message "Jira URL not reachable (DNS)" |
| HTTP 401 (user token mode) | "Authentication failed — check email/API token" |
| HTTP 401 (service account mode) | "Authentication failed — token expired or scopes missing. Please create a new token with scopes `read:jira-work`, `read:jira-user`." |
| HTTP 403 on `/myself` (SA mode) | "Service account has no Jira app access. Please ask the org admin to add the account to the group `jira-software-users-<site>`." |
| HTTP 403 on project | Worklogs from this project are skipped, warning in log: "Service account has no access to project X — likely missing the project role 'Users'." Export continues |
| HTTP 404 on cloud ID path | "Cloud ID wrong or site does not exist. Determine with `--discover-cloud-id <site-url>`." |
| HTTP 429 | Auto-retry respecting `Retry-After` |
| Empty result set | CSV with header but no data rows; notice in UI |
| Invalid date | Validation before export, hint at the field |
| No user selected | Export button stays disabled |
| Output file not writable | Error message with path, no partial write attempt |
| Invalid cloud ID format | UI-side validation against `^[0-9a-f-]{36}$` |

---

## 14. Build & Distribution

- **Repo host:** GitHub, public (since v1.0.0).
- **CI:** `.github/workflows/build-windows.yml` with trigger on tags `v*`.
  - Steps: Setup Python 3.12 → `pip install -e .[build]` → `pyinstaller jwe-gui.spec` → `pyinstaller jwe-cli.spec` → SHA-256 manifest → upload to GitHub release.
- **Artefacts:** `JiraWorklogExporter-GUI.exe`, `jwe-cli.exe`, `SHA256SUMS.txt`.
- **Versioning:** Semantic Versioning (`MAJOR.MINOR.PATCH`).
- **Code signing:** v1 unsigned; in v2 possibly with Sigstore / self-hosted cert.

---

## 15. Acceptance Criteria

| ID | Criterion |
|---|---|
| AC-01 | With a valid URL, email and token, `/myself` is called successfully and the display name is shown. |
| AC-02 | When a user is selected, a 30-day date range is set, and no project filter is given, all worklogs of this user in the selected days are exported. |
| AC-03 | CSV contains exactly the required columns project, issue key, issue summary, user, time spent, work description, and all data rows are fully filled (except optional fields like email). |
| AC-04 | CSV opens in Excel (DE) without encoding errors on umlauts and special characters. |
| AC-05 | ADF comments with bold text, lists and mentions are converted to readable plain text (lists with dashes, mentions as `@DisplayName`). |
| AC-06 | On a simulated 429 response, the client retries and completes the export successfully. |
| AC-07 | A 30-day export over 50,000 worklogs runs with < 200 MB RAM and correct row count in the CSV. |
| AC-08 | GitHub Actions workflow builds both executables successfully on a tag push and attaches them to the release. |
| AC-09 | Token inputs appear in no log and no stack trace. |
| AC-10 | CLI with `--dry-run` produces only statistics (number of issues, number of worklogs, sum of seconds) without CSV. |

---

## 16. Risks & Open Issues

| ID | Risk / Open question | Impact | Mitigation |
|---|---|---|---|
| R-01 | Atlassian deprecates v2 of the API; worklog comment ADF parsing becomes mandatory | medium | ADF parser robust from the start; v3 as default |
| R-02 | User email is not retrievable due to privacy settings | low | Column may be empty, no abort |
| R-03 | JQL operator `worklogAuthor` requires `View All Worklogs` permission on the projects | high | Document in README and PRE-03; fallback: search via `assignee` plus client-side filtering (significantly more expensive, therefore emergency only) |
| R-04 | Very large tenants: pagination may take hours | medium | Streaming CSV, cancel button, clear progress display |
| R-05 | Date filter `worklogDate` works in the timezone of the calling user — can lead to edge cases at day boundaries for distributed teams | low | Document in README; possibly option `--timezone` in v2 |
| R-06 | **Service account token rotation:** Tokens have max. 365 days lifetime; after creation scopes cannot be changed | medium | Hint in GUI when less than 30 days remaining; README section on rotation workflow; possibly keep two tokens in parallel for seamless switch |
| R-07 | **Service account limit of 5 per org** without Atlassian Guard | medium | A single account for all read-only evaluations is sufficient — clearly justified in README; fallback to user token mode if no SA slots free |
| R-08 | **Three-layer permission matrix** (app access ∩ project role ∩ token scope) often leads to hard-to-diagnose 401/403 with service accounts | high | Differentiated error messages (see §13); permission helper hint in README; CLI subcommand `jwe doctor` for diagnosis run |
| R-09 | Atlassian Agile/Software-specific endpoints are partially incompatible with service accounts | low | We use exclusively platform API (`/rest/api/3`), no Agile API. Check in v2 if needed. |
| R-10 | Atlassian changes the service account mechanics further (OAuth client credentials, new scope granularities) | medium | Modular auth strategy architecture; quarterly review of Atlassian roadmap |

**Open questions / clarifications with user:**

- ~~Should v1 already offer Excel (.xlsx) export, or is CSV sufficient?~~ → **Clarified: CSV is sufficient.**
- ~~Should the tool manage multiple Jira Cloud tenants in one session?~~ → **Clarified: No, one site per run.**
- ~~Is a configuration profile mechanism needed?~~ → **Clarified: Only v1.1.**
- **Newly open:** Is org admin permission for creating the service account in place? If not, v1 must start with user token mode and the SA mode is added later.
- **Newly open:** Should logs contain the service account display name (audit trail), or is that problematic from a privacy perspective? (Proposal: display name OK, mask email.)

---

## 17. Roadmap

| Version | Content |
|---|---|
| v1.0 | Core functionality per this PRD (CLI + GUI, Windows build) |
| v1.1 | Profiles (save/load filters as JSON), additional column profiles, .xlsx export |
| v1.2 | Jira Data Center support (PAT auth) |
| v2.0 | OAuth 2.0 Client Credentials Flow for service accounts (no more long-lived tokens); OAuth 2.0 (3LO) for interactive user login; evaluation dashboard (local, no server) |

---

## 18. Glossary

- **Worklog:** Individual time entry on a Jira issue (hours plus optional comment).
- **JQL:** Jira Query Language — search language for issues.
- **ADF:** Atlassian Document Format — JSON-based rich text format of API v3.
- **accountId:** Unique, non-personal ID of a Jira Cloud user (or service account).
- **API token:** Token generated at `id.atlassian.com` (user) or `admin.atlassian.com → Service accounts` (SA); replaces the password for API calls. Cloud tokens have been time-limited since Dec 2024 (max. 365 days).
- **Site:** A Jira/Confluence instance within an Atlassian organisation, e.g. `acme.atlassian.net`. An organisation can have multiple sites; this tool addresses exactly one site per run.
- **Cloud ID:** UUID that uniquely identifies a site. Required for API calls via the platform gateway.
- **Service account:** Non-personal Atlassian identity, exclusively for API access. Does not consume a licence, cannot log in interactively, managed by the org admin.
- **Scope:** Permission granularity of an API token. Mandatory for service account tokens and scoped user tokens; optional for classic (legacy) user tokens.
- **Platform gateway:** `https://api.atlassian.com/ex/jira/{cloudId}/...` — the API entry for scoped tokens. In contrast to the classic `https://<site>.atlassian.net/...`.
- **Granular scopes:** Finer-grained scope variant (e.g. `read:issue:jira` instead of `read:jira-work`). Recommended for new integrations.

---

## Appendix A: Setup Guide for the Org Admin (Service Account Mode)

This guide describes the one-time setup of a service account for the tool. Prerequisite: **Organisation admin role** (not just site admin).

### A.1 Create Service Account

1. Open `https://admin.atlassian.com`.
2. If multiple organisations exist: select the desired organisation.
3. In the left menu: **Directory → Service accounts**.
4. Click **Create service account**.
5. Name: e.g. `jwe-worklog-exporter` (convention: tool name plus purpose).
6. Description: purpose, responsible owner user, creation date, possibly ticket reference.
7. Save. Atlassian automatically generates an email of the form `<id>@serviceaccount.atlassian.com` — this is later needed for Basic Auth and should be noted.

### A.2 Grant App Access

The service account needs access to the Jira product:

1. Select the service account in the list → **Add to group**.
2. Add the group `jira-software-users-<site>` (or the comparable app access group of the site).
3. If Confluence/JSM is to be added later: add there too.

### A.3 Set Project Permissions

For every project whose worklogs should be exported:

1. In the site UI: open project → **Project settings → People** (or **Access** in newer layouts).
2. Add the service account (via email `<id>@serviceaccount.atlassian.com`).
3. Role: **Users** (or a project-specific role that allows at least `Browse Projects` and `View All Worklogs`).
4. **Important:** Without `View All Worklogs`, the JQL operator `worklogAuthor` does not take effect — the export stays empty. The Permission Helper under **Project settings → Permissions → Permission Helper** can verify this for a sample issue.

### A.4 Create API Token with Scopes

1. Back to `admin.atlassian.com → Directory → Service accounts`.
2. Select the service account just created.
3. **Actions → Create credential → API token**.
4. Name: `jwe-readonly-<date>` (convention: purpose plus creation date, helps on rotation).
5. **Expiration:** maximum 365 days. Recommendation: 90 or 180 days, with calendar reminder for rotation.
6. **Select scopes** — minimum:
   - `read:jira-work` (classic) **or** the granular equivalents:
     - `read:issue:jira`
     - `read:issue-worklog:jira`
     - `read:project:jira`
     - `read:jql:jira`
   - `read:jira-user` (classic) **or** `read:user:jira`
   - **No write or admin scopes!**
7. Click **Create**. The token is displayed **exactly once** — copy it immediately to a password manager or the CI/CD secret store. Atlassian does not store it.

> ⚠️ **Important:** Scopes **cannot be changed after token creation**. If a scope is missing later, a new token must be created with the desired scope set.

### A.5 Determine Cloud ID

The cloud ID is needed by the tool for the gateway URL. Three ways:

- **Automatic:** Run `jwe export --discover-cloud-id https://acme.atlassian.net`.
- **Via browser/curl:** `curl https://acme.atlassian.net/_edge/tenant_info` (anonymous endpoint, returns JSON with `cloudId`).
- **Via admin UI:** `admin.atlassian.com → Settings → Sites`. Select site — the cloud ID is part of the URL after `/s/` (e.g. `1a11d016-8984-4c3e-b9ab-142dd06acb1b`).

### A.6 Test Connection with the Tool

```bash
# Token in environment variable
export JWE_API_TOKEN="..."

# Connect test
jwe export \
  --auth-mode service-account \
  --cloud-id 1a11d016-8984-4c3e-b9ab-142dd06acb1b \
  --service-account-email jwe-worklog-exporter@serviceaccount.atlassian.com \
  --token-env JWE_API_TOKEN \
  --dry-run \
  --users <accountId> --from 2026-04-01 --to 2026-04-30
```

A successful `--dry-run` shows: "Authenticated as: jwe-worklog-exporter (accountId: …) — connection OK. 0 issues, 0 worklogs found in dry run."

### A.7 Token Rotation (every ≤ 365 days)

1. Create new token with identical scope set (step A.4).
2. Store new token in secret store in parallel to the old one.
3. Switch tool / consumers to new token.
4. Verify functionality.
5. Revoke old token in `admin.atlassian.com → Service accounts → <SA> → Actions → View API tokens → Revoke`.

### A.8 Cleanup When Decommissioning

1. Revoke all tokens of the service account.
2. Remove service account from project people lists (or optionally retain if audit history is important).
3. Remove service account from app access groups.
4. Delete service account (`admin.atlassian.com → Directory → Service accounts → Delete`).
