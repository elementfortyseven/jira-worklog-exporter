# CLAUDE.md — Jira Cloud Worklog Exporter

This file is the primary context for Claude Code working on this repository.
**Read it fully before making changes.** The PRD in `docs/PRD_Jira_Worklog_Exporter.md` is authoritative for requirements; this file is the developer's-eye view.

> **History note:** Release-by-release detail (v1.0.0/v1.0.1/v1.1.0 ticket logs),
> the original build order, and the completed GUI Stages 1–6 implementation/test
> breakdowns live in `docs/HISTORY.md`. That file is **not** `@`-imported, so it
> does not load into the session context — read it on demand when you need the
> archaeology. This file keeps only what steers current work.

---

## TL;DR

Python 3.12+ tool that exports Jira Cloud worklogs of selected users in a date range to CSV. Two binaries: a CLI (`jwe-cli`) and a PySide6 GUI (`jwe-gui`). Built for Windows via PyInstaller in GitHub Actions. The unusual part is the **dual authentication architecture** — see §3 below.

---

## 0. Operating instructions — read first

> **Note:** Some operating instructions are personal and live in
> `CLAUDE.local.md` (gitignored). The entries below are
> project-specific and apply to any contributor working on this
> codebase.

### Local verification must match CI scope

Run each tool without arguments so it checks the same scope as CI:

- **mypy:** `mypy` (no args) — checks all of `src/` per `pyproject.toml files = ["src"]`. Running `mypy src/jwe/gui/some_file.py` limits scope to that file and misses errors in others.
- **ruff:** `ruff check .` — already full-scope.
- **pytest:** `pytest` — already full-scope.

Running single-file mypy is the recurring trap: it can pass locally while CI fails because other files in `src/` contain errors.

### Framework bug research order

When a framework bug or unexpected library behavior appears, follow this order — each step can make the next unnecessary:

1. Search bug trackers, forums, and Stack Overflow for the symptom (is it a known issue?)
2. Read the official documentation of the affected component
3. Read the library source under `.venv/Lib/site-packages/` for implementation details
4. Check code repositories with working examples of the pattern in question — accompanying technical books, reference implementations, or established open-source projects with similar use cases
5. Only then: explore alternative solution patterns independently

Do not skip steps or start at step 5.

### Non-destructive diagnosis before reverting changes

Before using `git stash` or any other destructive operation to verify whether a regression was introduced by current changes, exhaust non-destructive diagnostic steps first:

1. Read the failing test code in full (not truncated output)
2. Read the actual error message including stack trace at full depth (no `Select-Object` truncation)
3. Check tool and dependency versions (`pip show`, `pip index versions`)
4. Check git log timing - when did the test last pass, what changed since?
5. Read the production code that the test exercises - is the test's assumption still valid?

Only after these steps come up empty: consider stash-based verification. The stash approach is valid but should be the fallback, not the first instinct. In practice the non-destructive path often resolves the question by itself, because the actual failure mode reveals itself in the code or environment.

### Coordinating direct-push and local sessions

This project occasionally uses direct-push via GitHub API or MCP for doc-only changes (such as CLAUDE.md updates from the architectural reviewer). When this happens, the next local Claude Code session must:

1. Pull from origin before reading any project files (`git fetch origin; git pull origin main`)
2. Re-read CLAUDE.md if it changed in the pull
3. Confirm HEAD matches origin/main before any further work

Direct-push commits do not appear in a local working tree until pulled. Starting a session against a stale tree leads to inconsistent doc references and missed convention updates. The architectural reviewer is responsible for prompting the user to pull after each direct-push, before the next session opens.

### Scope discipline for lint and type errors

Pre-existing lint, type, or other errors in files outside the current commit's scope are **reported, not silently fixed**. Resolution options:

- Fix in a **separate follow-up commit** with its own justification, or
- Leave in place with an **explicit decision** recorded in the commit message or chat.

Feature work and pre-existing bug fixes are never mixed in a single commit.

### GUI Stages workflow

One Stage = one commit = one fresh Claude Code session. At Stage completion update **§1** (status table) and **§14** (Stage heading → ✅) in the same commit as the code and tests.

### GUI review pattern

1. Class sketch with signal/slot list → wait for explicit approval before writing code
2. Write code — `# i18n: <key>` on every hardcoded string (Stages 2–5b)
3. Tests green + brief visual window description
4. Single commit: code + tests + §1 update + §14 ✅

### CLAUDE.md maintenance discipline

This document is updated as part of every commit that materially changes the project state. If the commit scope does not include a doc update, a follow-up `docs:` commit lands immediately.

Minimum scope for any update:

- **§1 status table** if a module's state, test count, or CI infrastructure changed
- **§13 backlog** if a known issue was resolved or a new one identified
- **§14 Stages** marked ✅ on completion (existing rule, see GUI Stages workflow above)

Version transitions (release of any `vX.Y.Z`) trigger a full review of §1, §13, and §14 in a dedicated `docs:` commit if not already current. At a version transition, append the release summary to `docs/HISTORY.md` rather than letting §1 grow — §1 records the *current* state, `HISTORY.md` records the trail.

---

## 1. Project state

**Phase:** v1.1.0 released (2026-06-09). CLI, service layer, and GUI core functionality are complete; the GUI is fully internationalised (two-channel i18n, runtime language switch, CLI `--lang`). The headless-CLI split (JWE-45) has landed: `jwe-cli` carries no Qt in its import graph. Next active work is the v1.2.0 visual redesign (epic JWE-32). Full release-by-release ticket history is in `docs/HISTORY.md`.

**Roadmap.**
- **v1.2.0** (target 2026-06-27) — purely visual redesign (epic JWE-32): dark "Technical/Mono" theme, frameless window shell + native Win32 chrome (JWE-34 + JWE-50 done), card-based section layout, on top of the existing PySide6 widget tree with **no functional change**. Earlier UX-polish items are absorbed here (JWE-3 → JWE-36 inline-validation border; JWE-4 absorbed into JWE-34 done). See §14.
- **v1.3.0** (target 2026-07-11) — User Management v2 (local SQLite cache, wildcard search, CSV/group import, presets; epic JWE-11) and the interaction redesign (replace the shuttle, multi-selects; epic JWE-12), built on the v1.2 theme.

**CI infrastructure.** GitHub Actions is the primary CI and the source of truth for releases (Windows builds attached to GitHub Releases at `v*` tags). GitLab CI (`.gitlab-ci.yml`, Stufe 1: tests only) runs alongside the mirror to give GitLab-only collaborators independent verification of every push to `main` and every tag; green since JWE-10 (QRadioButton click compat fix for the winrm executor). The mirror push to GitLab is **manual** (never from Claude Code).

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
| `jwe.i18n` | ✅ implemented | Two-channel model: STRINGS + t(key, lang) for localized presentation; DIAGNOSTICS + diag(key) for English-only log/error messages. 97% coverage, 244 tests. |
| `jwe.cli` | ✅ implemented | argparse with export and discover-cloud-id subcommands, exit codes 0-6, tqdm progress bar, KeyboardInterrupt drain loop; --lang on export subcommand; errors via diag(), progress/summary via t(key, lang); headless (no Qt in import graph); 83% coverage, 22 tests |
| `jwe.gui` | ✅ stages 1-5b + Stage 6 + JWE-34 + JWE-49 + JWE-50 + JWE-35 complete | Full GUI implementation: AuthWidget with dual-mode panels, UserSearchWidget with debounced search, FilterWidget, OutputWidget, StatusWidget with progress + cancel + result buttons; ExportWorker and UserSearchWorker via Pattern C (persistent worker threads with lazy start); closeEvent confirmation; QSettings round-trip for all persistent fields; full i18n (two-channel model, runtime language switch, QSettings persistence). Frameless window shell (JWE-34): FramelessWindowHint + WA_TranslucentBackground, #windowFrame with drop shadow, custom TitleBar (brand, DE/EN segmented toggle, min/max/close), edge resize via startSystemResize, manual maximize/restore with availableGeometry. JWE-49: resize hot-zone against outer rect + slim 10px shadow margin. JWE-50: native Win32 WM_NCHITTEST/WM_NCCALCSIZE via nativeEvent on Windows; DWM shadow + Win11 rounded corners; startSystemResize/Move fallback retained for non-Windows. Pure geometry helper _nc_hit_region tested offscreen (15 unit tests). JWE-35: SectionCard(QFrame) wraps all four sections (QGroupBox removed); icon badges (QPainter-drawn), [ NN ] index, title/subtitle, right-slot, accent tick; auth mode selector in auth card head-end; new section subtitle i18n keys; 918 tests green across the suite. |
| `jwe.gui.theme` | ✅ JWE-33 | Design tokens SSOT (tokens.py, Qt-free), QSS template (app.qss), apply_theme() loader with lazy Qt imports, bundled JetBrains Mono Regular/Medium/SemiBold + OFL.txt. 78 tests: parametrized drift guard (color/radius/space/font/type vs tokens.json), Qt-free import guard, QSS completeness, apply_theme() behavior, font registration. |
| `jwe.gui_main` | 🟡 stage 1 (skeleton) | QApplication bootstrapper; calls apply_theme() after setStyle("Fusion"); 0% unit coverage (requires display) |

Tests follow the same pattern: implemented for implemented modules, stubbed for the rest.

---

## 2. Run / dev workflow

Use forward slashes in Python source code; Python normalises them on Windows. Use `\` only when passing paths to Windows-specific CLI tools. Shell and commit conventions are in §0.

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
python -m jwe.gui_main

# Build Windows binaries locally (CI uses the same PyInstaller invocations; see build-windows.yml)
# jwe-cli excludes PySide6/shiboken6 to keep it headless (no Qt bundled); jwe-gui includes them.
pyinstaller --onefile --console --name jwe-cli --paths src --hidden-import keyring.backends.Windows --exclude-module PySide6 --exclude-module shiboken6 src/jwe/__main__.py
pyinstaller --onefile --windowed --name jwe-gui --paths src --hidden-import keyring.backends.Windows src/jwe/gui_main.py
```

The CI build (`.github/workflows/build-windows.yml`) invokes PyInstaller from the command line exactly as above; there are **no committed `.spec` files** (`*.spec` is gitignored). Any `.spec` you generate for local iteration stays local — the workflow is the authoritative build config.

**Headless CLI (JWE-45):** `jwe-cli` has no GUI subcommand and no Qt in its import graph. The packaged `jwe-cli.exe` excludes `PySide6` and `shiboken6`, making it significantly smaller than `jwe-gui.exe`. GUI initial language is set solely via saved QSettings and the runtime toggle — no `--lang` flag on any GUI launch path.

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

**Permission layer is AND-coupled with token scopes (not an alternative).** A token with the right scopes still returns zero worklogs if the account lacks the **Browse Projects** / **View All Worklogs** project permission. Both must be satisfied. This is the concrete failure mode the planned `jwe doctor` subcommand (JWE-47) is meant to diagnose.

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

## 7. Implementation order (historical)

All foundation modules are built and green (see the §1 status table). The original suggested build order and per-module notes are archived in `docs/HISTORY.md`. The one rule that still applies: when touching auth/URL plumbing, run `pytest tests/test_url_builder.py tests/test_auth.py` first — they must pass before anything else.

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
- **Shell commands target PowerShell, not bash.** See §0.

---

## 9. Testing strategy

- **Unit tests** for pure functions (URL builder, ADF parser, JQL builder, CSV writer) — these are the bulk.
- **Integration tests** for the API client are mocked with `responses` (already in dev deps). Don't hit a real Jira from CI.
- **Fixtures** for ADF samples, `/myself` responses, search responses, and worklog responses live in `tests/fixtures/`.
- **End-to-end test** is manual: run `--dry-run` against a real tenant; not in CI.
- Test data in fixtures uses fake but realistic accountIds and emails.

### Headless Windows considerations for GUI tests

GitLab Windows runners use the winrm executor (non-interactive session). `qtbot.mouseClick` on `QRadioButton` is unreliable in this environment because mouse events depend on the widget being exposed and the session being interactive. `QPushButton` clicks are more tolerant and work on both GitHub and GitLab. **Convention:** for radio button state changes in tests, prefer `radio.click()` or `radio.setChecked(True)` over `qtbot.mouseClick`.

### Fixture cleanup discipline for QThread-bearing widgets

GUI test fixtures that create widgets with persistent QThreads must be generator fixtures with explicit `w.close()` teardown. This triggers `closeEvent`, which stops all persistent threads cleanly. Without teardown, threads may outlive the test, leak into Python's cyclic GC scope, and crash the test session at interpreter shutdown with `QThread: Destroyed while thread '' is still running` (exit code 9). See JWE-26 commit message for the full diagnostic chain.

Additionally, widgets that start QThreads lazily based on timer events (debounce timer, etc.) must stop those timers in `stop_running_threads()` to prevent a late-firing timer from starting a thread *after* fixture cleanup has run. The convention: `stop_running_threads()` stops timers first, then quits the thread.

### Teardown-contract assertion convention

Every persistent `QThread` managed by a widget must have at least one test that verifies the `closeEvent` actually stops it. The pattern:

1. Start the thread directly (e.g. `w._export_thread.start()`) — do not rely on a never-started thread being trivially not-running.
2. Assert `isRunning()` is `True` before closing, to prove the thread was genuinely started.
3. Call `w.close()` to trigger `closeEvent`.
4. Assert `isRunning()` is `False` to confirm quit()+wait() ran to completion.

This guards against production paths where the thread could be GC-destroyed while still running (exit code 9 crash). See `TestCloseEventTeardown` in `tests/gui/test_main_window.py`.

### Date and time coincidence in tests

**Bug class:** a no-op setter followed by a change-signal expectation. `widget.setX(value)` emits no change signal when `value` already equals the widget's current value. If a `waitSignal` follows, it times out. The symmetric form is `setText("")` on a field whose current value is already `""`.

For `FilterWidget` the collision targets are:
- `from_date` default = first day of current month (always day 1)
- `to_date` default = last day of current month (always day 28–31)
- `project_keys_field` default = `""` (empty string)

**Convention:** use a fixed `QDate` with day-of-month in the range 2–27 (canonical: the 15th, e.g. `QDate(2025, 1, 15)`). Such a date can never equal a day-1 or day-28..31 default for *any* runtime "today" — collision-proof by construction. Use a past year to avoid forward-coincidence.

Apply this rule to **all** `setDate` calls in tests that touch `FilterWidget` (or any date widget whose default is the current date), even when no `waitSignal` follows. Consistent use makes every date-touching test structurally clock-independent.

**Do not use freezegun** to simulate "today": it patches Python's `datetime`, not Qt's `QDate.currentDate()` (a C++ static call), so it would not affect `FilterWidget` defaults.

For `setText("")` on a field that may default to `""`: ensure the field already contains a non-empty value before calling `setText("")` if a change signal is expected. See the comment in `test_user_search_widget.py` line ~155 for an example.

### Security tooling in CI (JWE-23)

Both GitHub Actions and GitLab CI run a dedicated `security` job on every push (Ubuntu/Python 3.12):

- **bandit** — `bandit -r src -c pyproject.toml -ll` gates at medium-and-above severity. To suppress a finding at the call site: `# nosec <ID>  # reason` (the reason is required for review).
- **pip-audit** — blocking; reports known CVEs in all installed packages. To allowlist an unfixable transitive advisory: `pip-audit --ignore-vuln <ID>` in the workflow (document the reason inline).

### Versioning (JWE-43)

`__version__` in `src/jwe/__init__.py` is the single source of truth; `pyproject.toml` derives the version via hatchling dynamic versioning. Bump the version only at release boundaries via a `vX.Y.Z` tag, which triggers the Windows binary build and GitHub Release. Milestone or test builds use pre-release tags (`vX.Y.Z-rc1`, published as GitHub pre-releases) — never an ad-hoc version bump in source.

**Version-bump encoding gotcha:** when rewriting version strings or any UTF-8 content from PowerShell, do **not** use `Set-Content` (it adds a BOM and can mangle non-ASCII such as `→`). Use:

```powershell
[IO.File]::WriteAllText($path, $text, (New-Object Text.UTF8Encoding $false))
```

---

## 10. Known traps (in priority order)

1. **Wrong base URL with service-account token** → 401 with no helpful message. Always go through `URLBuilder`.
2. **Missing `View All Worklogs` / `Browse Projects` permission** → empty results, no error. The permission layer is AND-coupled with token scopes (§3). Cross-check by counting issues found vs. worklogs returned and warn if the ratio looks suspicious.
3. **Scope-locked tokens** → 403 on specific endpoints only. Mode A error handler should mention this possibility.
4. **ADF with embedded mentions and inline cards** → naive text extraction loses the user reference. The fixture covers this.
5. **Pagination off-by-one** with `startAt`/`maxResults` (worklogs) vs. `nextPageToken` (search) — they're different APIs with different mechanisms.
6. **DE Excel and CSV encoding** — UTF-8 BOM is non-negotiable; without it, umlauts break in Excel DE.
7. **PySide6 main thread and workers** — never call Qt widgets from a worker thread. Use `QThread` + signals/slots; emit progress via custom signals only.

---

## 11. References

- PRD: `docs/PRD_Jira_Worklog_Exporter.md`
- Release & build history: `docs/HISTORY.md`
- Atlassian REST API v3: https://developer.atlassian.com/cloud/jira/platform/rest/v3/
- Service Accounts: https://support.atlassian.com/user-management/docs/manage-api-tokens-for-service-accounts/

---

## 12. When in doubt

- Re-read §3 (dual authentication).
- Check the PRD's acceptance criteria (§15) — they're the spec for "done."
- If a library wants to hide auth/URL details, **don't use it**. The whole point of this project's architecture is keeping that layer explicit.

---

## 13. Backlog / known UX issues

- **Output dir auto-create:** Currently `ExportConfig.validate()` raises if `output_dir` does not exist. For better UX, the default `./exports` should be auto-created on first run, while explicitly user-provided paths still raise (protects against typos). Pick this up during the GUI iteration since the file-picker will need consistent behavior.
- **Cross-platform builds:** Add `build-macos.yml` and `build-linux.yml` GitHub Actions workflows after the first GUI implementation. macOS requires Code Signing and Notarization; Linux is best packaged as AppImage. Initially acceptable without signing for internal distribution — document the bypass procedure for users.
- **`jwe doctor` diagnostic subcommand (JWE-47):** a preflight that checks auth, scopes, and the AND-coupled project-permission layer (Browse Projects / View All Worklogs), so a zero-worklog export is explained rather than silent. The production zero-worklog incident (missing Browse Projects on a scoped token) is the canonical test case.

> Resolved backlog items (JWE-6, JWE-7, and the v1.1.0/v1.0.1 follow-ups) are archived in `docs/HISTORY.md`.

---

## 14. GUI roadmap — conventions & active stages

Stages 1–6 are complete (v1.0.0 → v1.1.0). Their full implementation/test breakdowns are archived in `docs/HISTORY.md`. The conventions below are **permanent** and apply to every remaining stage (the v1.2 redesign stories JWE-33…40 and beyond).

### i18n-Marker convention (Stages 2–5b)

Every hardcoded UI string (label text, button caption, placeholder, error message) that is not yet wired to `t()` must be annotated inline:

```python
self.label.setText("Connection test")  # i18n: auth.btn.test_connection
```

This makes a later i18n refactoring mechanical (grep for `# i18n:`) rather than a hunt through the codebase.

### Two-channel i18n convention (established in Stage 6, applies permanently)

**Logging and all error/failure messages are always English** (`DIAGNOSTICS` / `diag(key, **kwargs)`, no `lang` param). Only UI chrome — labels, buttons, titles, placeholders, dialogs, and CLI progress/summary — is localized (`STRINGS` / `t(key, lang, **kwargs)`). This keeps logs grep-able and troubleshooting single-language regardless of the user's selected locale.

Rule of thumb: if the string appears in a log file or in response to an error condition, use `diag()`. If the user reads it in the normal operating flow, use `t(key, lang)`.

The `test_no_i18n_markers_remain_in_src` test in `tests/test_i18n.py` gates regressions: any new hardcoded UI string that is not immediately wired through `t()` or `diag()` will cause CI to fail.

### v1.2 — Visual redesign (epic JWE-32)

A purely visual and structural re-skin on top of the existing PySide6 widget tree — no change to data flow, auth, export, CSV, or threading logic. Direction "Technical/Mono": navy base, cyan neon accent, monospace labels/numbers, bracketed section indices, card-based sections, terminal-style export log. The interactive prototype lives outside the repo (`JWE Redesign.html`); the prototype and the extracted token values should be committed under `docs/design/` before JWE-33 starts (tracked as JWE-48).

**Web → QSS translation (plan for this in JWE-33):** the prototype and any Claude Design output are web artifacts (HTML/CSS/JS); the target is Qt with QSS, which is a CSS *subset* — no flexbox/grid, a limited selector set, and no CSS transitions/animations. Treat the prototype as a *visual spec*: token *values* (palette, spacing, radii, font sizes/families) port 1:1 into `theme/tokens.py`, but layout is rebuilt with Qt layouts and motion is re-expressed via `QPropertyAnimation`/`QTimer`. Do not paste web CSS into `app.qss`. JWE-48 produces the prototype + tokens (via Claude Design, which can refine the existing `JWE Redesign.html`); JWE-33 consumes the token *values*, not the markup.

New architecture introduced here (all under `jwe/gui/`):
- `theme/tokens.py` — single source of truth for palette, spacing, radii, font roles (no Qt import)
- `theme/app.qss` — central stylesheet loaded once on QApplication startup; Fusion stays the base style
- `widgets/section_card.py` — reusable numbered card wrapping each of the four sections
- a frameless `MainWindow` (custom title bar with DE/EN toggle, min/max/close, window move) replacing OS chrome
- restyled form controls, identity strip + status chips, themed export footer, and a motion layer (`QPropertyAnimation`/`QTimer`/`QGraphicsDropShadowEffect`) with a reduced-motion fallback

Child stories: JWE-33 ✅ (tokens/theme), JWE-34 ✅ (frameless shell, absorbs JWE-4), JWE-49 ✅ (edge resize fix, shadow margin), JWE-50 ✅ (native Win32 chrome), JWE-35 ✅ (section cards, QGroupBox->QWidget), JWE-36 (form controls, absorbs JWE-3's error border), JWE-37 (identity strip/chips), JWE-38 (interim user/chip styling, pre-JWE-12), JWE-39 (export footer), JWE-40 (motion). Keep the auth-mode controls as `QRadioButton`s (styled as a segmented control) for winrm test compatibility per §9. Each story stays one Stage = one commit = one session; §1 and this section are updated on completion.

**JWE-33 delivered (2026-06-20):** `jwe/gui/theme/` created: `tokens.py` (SSOT mirror of `docs/design/tokens.json`, Qt-free, importable without PySide6), `app.qss` (QSS template with `%(key)s` placeholders for all token values), `__init__.py` with `apply_theme(app)` (lazy Qt imports — deferred to function bodies so the package can be imported without loading Qt). Bundled JetBrains Mono Regular/Medium/SemiBold + OFL.txt. `gui_main.py` calls `apply_theme()` after `setStyle("Fusion")`. `jwe/gui/__init__.py` refactored to lazy `__getattr__` re-export (prerequisite for the Qt-free import guard). `build-windows.yml` ships QSS and fonts via `--add-data` on the jwe-gui step; `pyproject.toml` declares them via `force-include`. 78 new tests green; full suite 832 passed.

**JWE-34 delivered (2026-06-20):** Frameless window shell replacing OS chrome. `MainWindow` sets `FramelessWindowHint` + `WA_TranslucentBackground`; the central widget carries a 32px transparent margin for the drop shadow, inside which sits `#windowFrame` (QFrame with `QGraphicsDropShadowEffect` from `WINDOW_SHADOW` token). New widget `jwe/gui/widgets/title_bar.py` (`TitleBar(QFrame)`) provides the brand label (rich-text "Worklog" emphasis in accent color), a DE/EN segmented toggle (two `QPushButton`s with `active` dynamic property + re-polish), and min/max/close window control buttons; signals wire to `MainWindow._on_language_selected`, `showMinimized`, `_toggle_max_restore`, and `close`. Old `lang_btn` / `_target_flag` / `_toggle_language` removed. Window move via `startSystemMove` on title-bar drag; edge resize via `startSystemResize` on `_edge_at_pos` hit-test (6px margin); maximize uses `screen().availableGeometry()`, disables the shadow, sets `border-radius: 0` via `maximized` dynamic property; normal geometry saved in `_pre_max_geometry` (`QByteArray` from `saveGeometry()`) so restore does not return pseudo-maximized. `app.qss` extended with `#windowFrame`, `#titleBar`, `#titleLangBtn[active]`, `#winMin/#winMax/#winClose` rules; no new tokens added. 22 new tests; full suite 854 passed. JWE-4 absorbed (min window size 800x600 preserved). JWE-49 (2026-06-22): `_edge_at_pos` rewritten to detect edges against the window outer rect (transparent margin, no interactive children) instead of a band inside `#windowFrame` that child widgets shadowed; `_SHADOW_MARGIN` slimmed from 32px to 10px; 9 new geometry tests; full suite 863 passed.

**JWE-50 delivered (2026-06-22):** Native Win32 window chrome via WM_NCHITTEST/WM_NCCALCSIZE. On Windows: `FramelessWindowHint`, `WA_TranslucentBackground`, `QGraphicsDropShadowEffect`, and the `_SHADOW_MARGIN` ring are removed; the window is a normal OS window and DWM provides the drop shadow + Win11 rounded corners (via `DwmExtendFrameIntoClientArea(-1,-1,-1,-1)` and `DwmSetWindowAttribute(DWMWA_WINDOW_CORNER_PREFERENCE, DWMWCP_ROUND)`). `nativeEvent` handles WM_NCCALCSIZE (zeroes non-client area; insets by DPI-aware resize border when maximized) and WM_NCHITTEST (delegates to pure static helper `_nc_hit_region`). Maximize/restore uses native `showMaximized()`/`showNormal()`; `changeEvent(WindowStateChange)` syncs `_maximized` for native snap-maximize. Non-Windows: the JWE-34/49 `startSystemResize`/`startSystemMove` frameless path is retained, guarded by `sys.platform != "win32"`. `TitleBar.set_maximized()` added to toggle the maximize/restore glyph from both the Windows and non-Windows paths. `#windowFrame` border changed to 2px. 15 new `_nc_hit_region` geometry unit tests + 4 `TitleBar.set_maximized` tests; 5 existing tests marked `skipif(win32)` (frameless/shadow/pre_max_geometry). Full suite: 881 passed, 5 skipped.

**JWE-35 delivered (2026-06-26):** Section cards replace QGroupBox in all four section widgets. New `jwe/gui/widgets/section_card.py`: `SectionCard(QFrame)` with objectName `sectionCard`; QPainter-drawn icon badge (30x30, `sectionIcon`, accent bg/border); monospace index label `[ NN ]` (`sectionIndex`); title (`sectionTitle`, 15px/600) and subtitle (`sectionSubtitle`, 11px/tx-3); right-slot `sectionHeadEnd` via `set_head_widget()`; `QVBoxLayout` content area via `content_layout()`; 26x2 accent-colour tick `sectionTick` at position (20, 0). Four icons (QPainter geometry, accent stroke): plug (auth), users (user search), calendar (filter), output. `AuthWidget`, `UserSearchWidget`, `FilterWidget`, `OutputWidget` converted from `QGroupBox` to `QWidget`; margins zeroed; `setTitle` removed from `retranslate_ui`; auth mode selector (SA/Personal radios) exposed as `auth_mode_selector` and placed in the auth card right-slot by `MainWindow._build_ui`. `app.qss` gains `#sectionCard`, `#sectionIcon`, `#sectionIndex`, `#sectionTitle`, `#sectionSubtitle`, `#sectionTick` rules; QGroupBox rules retained for future use. New i18n subtitle keys: `section.auth.subtitle`, `section.users.subtitle`, `section.filter.subtitle`, `section.output.subtitle` (DE + EN). Side-fix: `FilterWidget` title key `"Date & Project Filter"` no longer creates an accidental keyboard-shortcut mnemonic (was a QGroupBox `&`-in-title artefact). 37 new tests (27 SectionCard offscreen + 8 i18n parity + 2 updated runtime tests); full suite: 918 passed, 5 skipped.

### Review pattern (mandatory for every stage)

1. **Class sketch** — present class names, inheritance, and the key signals/slots in prose first.
   Wait for explicit approval. The test list in the sketch must follow two rules:
   - **Field presence individually**: each UI field gets its own test (not "SA panel has the correct
     fields" as a single test).
   - **Plan negative cases**: for every "A leads to B" test, also note "not-A does not lead to B"
     (e.g. "checkbox off -> save_token NOT called"). In practice this roughly doubles the test count
     versus the first estimate.
2. **Write code** — `# i18n: <key>` on every hardcoded string (Stages 2–5b), no duplicates,
   ruff- and mypy-clean.
3. **Tests green + visual check** — `pytest` passes; the running window is briefly described
   (no screenshot test).
4. **Commit + push + §1 and §14 update** — update the CLAUDE.md §1 status table in the same commit;
   set the completed stage header in §14 to ✅.
