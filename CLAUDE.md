# CLAUDE.md — Jira Cloud Worklog Exporter

This file is the primary context for Claude Code working on this repository.
**Read it fully before making changes.** The PRD in `docs/PRD_Jira_Worklog_Exporter.md` is authoritative for requirements; this file is the developer's-eye view.

---

## TL;DR

Python 3.11+ tool that exports Jira Cloud worklogs of selected users in a date range to CSV. Two binaries: a CLI (`jwe-cli`) and a Tkinter GUI (`jwe-gui`). Built for Windows via PyInstaller in GitHub Actions. The unusual part is the **dual authentication architecture** — see §3 below.

---

## 1. Project state

**Phase:** v0 / skeleton. Architectural foundations are implemented; business logic is stubbed.

| Module | State | Notes |
|---|---|---|
| `jwe.api.auth` | ✅ implemented | AuthStrategy abstraction with two concrete classes |
| `jwe.api.url_builder` | ✅ implemented | Maps auth mode → base URL |
| `jwe.api.tenant_info` | ✅ implemented | Cloud ID discovery via `/_edge/tenant_info` |
| `jwe.api.client` | ✅ implemented | connect() and request() with typed exceptions; 100% coverage, 24 tests |
| `jwe.api.search` | ✅ implemented | build_jql and iter_issues with nextPageToken pagination; 100% coverage, 10 tests |
| `jwe.api.worklog` | ✅ implemented | iter_worklogs with offset pagination; 100% coverage, 8 tests |
| `jwe.api.user` | ✅ implemented | get_myself and search_users; 100% coverage, 7 tests |
| `jwe.adf` | ✅ implemented | adf_to_text recursive walker; 100% coverage, 28 tests |
| `jwe.config` | ✅ implemented | ExportConfig dataclass with validate, to_redacted_dict, and build_auth(); 100% coverage, 30 tests |
| `jwe.csv_writer` | ✅ implemented | WorklogCsvWriter context manager; 97% coverage, 15 tests |
| `jwe.exporter` | ✅ implemented | run_export generator; 90% coverage, 8 tests |
| `jwe.service` | ✅ implemented | Service layer (test_connection, search_users, discover_cloud_id, run_export, token persistence, config_from_env); 97% coverage, 12 tests |
| `jwe.i18n` | ✅ implemented | t(key, lang, **kwargs) with de/en tables; 95% coverage, 45 tests |
| `jwe.cli` | ✅ implemented | argparse with export and discover-cloud-id subcommands, exit codes 0-6, tqdm progress bar, KeyboardInterrupt drain loop; 83% coverage, 19 tests |
| `jwe.gui` | 🟡 stub | Tkinter UI |

Tests follow the same pattern: implemented for implemented modules, stubbed for the rest.

---

## 2. Run / dev workflow

This is a Windows-first project. The user develops on Windows 11 with VS Code. Use forward slashes in code (Python handles them); use `\` only when shelling out to Windows-specific tools.

```powershell
# One-time setup
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"

# Run tests
pytest

# Lint / format
ruff check .
ruff format .

# Run CLI from source
python -m jwe export --help

# Run GUI from source
python -m jwe gui

# Build Windows binaries (also runs in CI)
pyinstaller jwe-cli.spec
pyinstaller jwe-gui.spec
```

`.spec` files for PyInstaller are not yet generated — create them on first build with `pyinstaller --onefile --name jwe-cli src/jwe/__main__.py` and edit afterward.

### Shell environment

This project runs on Windows 11 with PowerShell as the primary shell.
Avoid Bash-specific syntax in any shell commands you generate:

- **No heredocs** (`cat <<'EOF' ... EOF`) — use PowerShell here-strings
  (`@"..."@`) or, for `git commit`, multiple `-m` flags instead.
- **No `&&` or `||` for command chaining** — use `;` for sequential
  execution or separate invocations.
- **No POSIX environment-variable syntax** (`export VAR=value`,
  `$VAR`) — use `$env:VAR = "value"` and reference as `$env:VAR`.
- **No POSIX pipe-and-redirect tricks** like `cat file | grep pattern` —
  use `Get-Content` / `Select-String` / PowerShell pipelines, or invoke
  the relevant tool directly.
- **Commit messages**: do not append `Co-Authored-By: Claude` trailers.

Git Bash is available on the user's machine for any tool that genuinely
requires bash, but normal development workflows go through PowerShell.

#### Troubleshooting: git push from Claude Code fails with publickey error

Symptom: `ssh -T git@github.com` succeeds from any shell, but `git push`
fails with "Permission denied (publickey)" specifically when invoked
from Claude Code's subshell.

Cause: Git for Windows ships its own bundled `ssh.exe` (under the Git
install's `usr/bin/`), which Git invokes for SSH operations regardless
of `PATH`. The bundled SSH does not communicate with the Windows
OpenSSH agent, where your loaded key lives.

Fix: point Git at the Windows OpenSSH binary explicitly:

    git config --global core.sshCommand "C:/Windows/System32/OpenSSH/ssh.exe"

This is a one-time machine-level setting and applies to all Git repos
on the host.

---

## 3. The architectural cornerstone: dual authentication

**This is the single most important thing to understand.** Atlassian Cloud has two distinct authentication regimes for REST APIs, and they require *different base URLs*. Most Python Jira libraries (e.g. `atlassian-python-api`, `jira`) hardcode the legacy URL and silently fail with service accounts. We don't use those libraries — we build our own thin client.

### Mode A: Service Account (preferred)

- Identity: a non-human Atlassian account managed in `admin.atlassian.com → Directory → Service accounts`.
- Email format: `<id>@serviceaccount.atlassian.com`.
- Token: must be created **with scopes** (Atlassian enforces this for service accounts).
- **Base URL: `https://api.atlassian.com/ex/jira/{cloudId}/rest/api/3/...`**
- Auth header: Basic (`email:token`) or Bearer (`Bearer <token>`); we default to Basic.
- Cloud ID: a UUID identifying the site. Required. Discoverable via `https://<site>.atlassian.net/_edge/tenant_info` (anonymous endpoint).

### Mode B: Personal API token (fallback)

- Identity: a regular human user.
- Token: created at `id.atlassian.com/manage-profile/security/api-tokens`. May or may not have scopes.
- **Base URL: `https://<site>.atlassian.net/rest/api/3/...`**
- Auth header: Basic only (`email:token`).

### Why this matters at every layer

- `url_builder.py` decides which base URL to use given the auth mode.
- `auth.py` produces the right `Authorization` header.
- `client.py` composes both; **never reach for `requests` directly elsewhere**.
- The CLI surface and GUI both have to expose the choice cleanly.
- Error messages need to differentiate: a 401 in Mode A often means *scopes missing*, not *bad token*.

### Required scopes for our read-only use case

Classic: `read:jira-work`, `read:jira-user`.
Granular (if the tenant supports them): `read:issue:jira`, `read:issue-worklog:jira`, `read:user:jira`, `read:project:jira`, `read:jql:jira`.

**Critical gotcha: scopes cannot be edited after token creation.** Token rotation = re-pick all scopes. Document this in user-facing error messages.

---

## 4. Data flow

```
config (CLI/GUI)
  ↓
Auth + URL builder
  ↓
JiraCloudClient.connect() → GET /myself      (verify auth)
  ↓
User resolution (accountIds)                 (api/user.py)
  ↓
JQL builder
  ↓
Search.iter_issues(jql)  ─paginated nextPageToken→  yields IssueRef
  ↓
Worklog.iter_worklogs(issueKey, since, until)  ─paginated→  yields Worklog
  ↓
client-side filter: author.accountId ∈ selected_users   (safety net)
  ↓
ADF → plain text                                       (adf.py)
  ↓
CsvWriter.append_row(...)                              (streaming)
  ↓
done: report stats
```

The Worklog comment lives in **ADF** (Atlassian Document Format) — a JSON tree. Don't try to render it; flatten to plain text. Common node types: `paragraph`, `text`, `hardBreak`, `bulletList` / `orderedList` / `listItem`, `mention`, `inlineCard`, `codeBlock`, `heading`. Mentions render as `@DisplayName`. See `tests/fixtures/adf_samples.json` for examples to test against.

---

## 5. JQL, exactly

The export is driven by one JQL query, then per-issue worklog calls.

```
worklogAuthor in ("accountId1", "accountId2")
AND worklogDate >= "2026-04-01"
AND worklogDate <= "2026-04-30"
AND project in (PROJ, SUPP)            # optional
```

Notes:
- `worklogAuthor` requires the **View All Worklogs** permission on each project. Without it, the query silently returns fewer results than expected. Document this prominently.
- accountIds in JQL must be quoted strings; escape any embedded quotes (defense-in-depth even if Atlassian IDs don't contain quotes today).
- `worklogDate` is a *date* (no time), evaluated in the calling user's timezone. Edge cases at day boundaries are documented as a known limitation.
- The Search API has migrated to `POST /rest/api/3/search/jql` with `nextPageToken` pagination. The old `GET /search` is deprecated. Use the new one.

For per-issue worklog fetching, use `startedAfter` and `startedBefore` as **Unix epoch milliseconds** to narrow down on the API side.

---

## 6. CSV output spec

UTF-8 with BOM (`utf-8-sig`), comma-delimited (configurable to `;` for German Excel), `csv.QUOTE_MINIMAL`. **Stream the output** — do not accumulate all worklogs in memory; flush after every row. This keeps RAM bounded for 100k+ row exports.

Three column profiles:
- `minimal` — the six required by the spec: `project_key`, `issue_key`, `issue_summary`, `worklog_author_displayname`, `time_spent`, `work_description`
- `standard` (default) — minimal + `project_name`, `worklog_author_email`, `worklog_started`, `time_spent_seconds`
- `full` — standard + `worklog_author_account_id`, `worklog_id`, `worklog_created`, `worklog_updated`

Default file name: `jira_worklogs_<from>_<to>_<timestamp>.csv`.

---

## 7. Implementation order (suggested)

1. **Verify foundations.** Run `pytest tests/test_url_builder.py tests/test_auth.py` — they must pass before touching anything else.
2. ✅ **`jwe.api.client`** — finish `connect()` and a generic `request()` method that uses the AuthStrategy + URLBuilder. Wire up retry on 429/5xx with respect for `Retry-After`.
3. ✅ **`jwe.adf`** — pure function `adf_to_text(adf_node) -> str`. Easiest to test in isolation; build with the fixture file.
4. ✅ **`jwe.api.user`** — `search_users(query) -> list[User]` and `get_myself() -> User`.
5. ✅ **`jwe.api.search`** — `iter_issues(jql, fields) -> Iterator[IssueRef]` with `nextPageToken` pagination.
6. ✅ **`jwe.api.worklog`** — `iter_worklogs(issue_key, since, until) -> Iterator[Worklog]` with offset pagination.
7. ✅ **`jwe.config`** — dataclass capturing every CLI/GUI input. Validation lives here.
8. ✅ **`jwe.csv_writer`** — context manager that opens the file, writes header, appends rows, flushes per row.
9. ✅ **`jwe.exporter`** — orchestrate everything. This is where the data flow in §4 lives.
9.5. ✅ **`jwe.service`** — service layer consumed by both CLI and GUI. Wraps test_connection, search_users, discover_cloud_id, run_export, keyring-based token persistence, and config_from_env. CLI and GUI import from here, not from exporter/user/tenant_info directly. `ExportConfig.build_auth()` was added to config as part of this step so auth-strategy construction lives in exactly one place.
10. ✅ **`jwe.cli`** — argparse, env-var fallback, exit codes per PRD §11.
11. ✅ **`jwe.i18n`** — t(key, lang, **kwargs) with de/en tables, KeyError on unknown key, en fallback for unknown lang.
12. **`jwe.gui`** — last, because by this point all the building blocks exist. Don't block the Tk main loop on long-running calls; run the export in a worker thread and post progress events back via a `queue.Queue`.

---

## 8. Style and conventions

- **Type hints everywhere.** `mypy --strict` on `src/`.
- **Dataclasses over dicts** for any value with named fields.
- **Iterators over lists** for paginated API results.
- **No global state.** Pass clients/configs explicitly.
- **Logging:** module-level `logger = logging.getLogger(__name__)`. Never `print()` outside of `cli.py`'s top-level user output.
- **Never log token values.** The `AuthStrategy.__repr__` masks the token; preserve that pattern.
- **Imports:** standard lib first, third-party second, local last. Ruff handles ordering.
- **Docstrings:** Google style. The first line is one sentence. Keep them brief.
- **Error messages are user-facing.** Especially for auth failures, give the user a concrete next step (see PRD §13).
- **No print-debugging committed.** Use `logger.debug` and `--verbose`.
- **Shell commands target PowerShell, not bash.** See §2.

---

## 9. Testing strategy

- **Unit tests** for pure functions (URL builder, ADF parser, JQL builder, CSV writer) — these are the bulk.
- **Integration tests** for the API client are mocked with `responses` (already in dev deps). Don't hit a real Jira from CI.
- **Fixtures** for ADF samples, `/myself` responses, search responses, and worklog responses live in `tests/fixtures/`.
- **End-to-end test** is manual: run `--dry-run` against a real tenant; not in CI.
- Test data in fixtures uses fake but realistic accountIds and emails.

---

## 10. Known traps (in priority order)

1. **Wrong base URL with service-account token** → 401 with no helpful message. Always go through `URLBuilder`.
2. **Missing `View All Worklogs` permission** → empty results, no error. Cross-check by counting issues found vs. worklogs returned and warn if the ratio looks suspicious.
3. **Scope-locked tokens** → 403 on specific endpoints only. Mode A error handler should mention this possibility.
4. **ADF with embedded mentions and inline cards** → naive text extraction loses the user reference. The fixture covers this.
5. **Pagination off-by-one** with `startAt`/`maxResults` (worklogs) vs. `nextPageToken` (search) — they're different APIs with different mechanisms.
6. **DE Excel and CSV encoding** — UTF-8 BOM is non-negotiable; without it, umlauts break in Excel DE.
7. **Tk main loop and threads** — never call Tk widgets from a worker thread. Use `queue.Queue` + `after(100, poll)` pattern.

---

## 11. References

- PRD: `docs/PRD_Jira_Worklog_Exporter.md`
- Atlassian REST API v3: https://developer.atlassian.com/cloud/jira/platform/rest/v3/
- Service Accounts: https://support.atlassian.com/user-management/docs/manage-api-tokens-for-service-accounts/
- Sister project (similar auth/build pattern): `jira-lead-exporter`

---

## 12. When in doubt

- Re-read §3 (dual authentication).
- Check the PRD's acceptance criteria (§15) — they're the spec for "done."
- If a library wants to hide auth/URL details, **don't use it**. The whole point of this project's architecture is keeping that layer explicit.
