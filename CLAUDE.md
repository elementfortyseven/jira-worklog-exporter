# CLAUDE.md — Jira Cloud Worklog Exporter

This file is the primary context for Claude Code working on this repository.
**Read it fully before making changes.** The PRD in `docs/PRD_Jira_Worklog_Exporter.md` is authoritative for requirements; this file is the developer's-eye view.

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

### GUI Etappen workflow

One Etappe = one commit = one fresh Claude Code session. At Etappe completion update **§1** (status table) and **§14** (Etappe heading → ✅) in the same commit as the code and tests.

### GUI review pattern

1. Class sketch with signal/slot list → wait for explicit approval before writing code
2. Write code — `# i18n: <key>` on every hardcoded string (Etappen 2–5b)
3. Tests green + brief visual window description
4. Single commit: code + tests + §1 update + §14 ✅

### CLAUDE.md maintenance discipline

This document is updated as part of every commit that materially changes the project state. If the commit scope does not include a doc update, a follow-up `docs:` commit lands immediately.

Minimum scope for any update:

- **§1 status table** if a module's state, test count, or CI infrastructure changed
- **§13 backlog** if a known issue was resolved or a new one identified
- **§14 Etappen** marked ✅ on completion (existing rule, see GUI Etappen workflow above)

Version transitions (release of any `vX.Y.Z`) trigger a full review of §1, §13, and §14 in a dedicated `docs:` commit if not already current.

---

## 1. Project state

**Phase:** v1.0.1 released (2026-06-02). It shipped the UserSearchWorker Pattern C refactor (JWE-26, fixes crash on fast typing) and the keyring backend bundling fix (JWE-27, restores the "Save token to keyring" feature in shipped binaries). Two follow-ups were then resolved against `main`: JWE-31 (the three win32-skipped two-instance MainWindow tests are un-skipped and green; the flake was cold-start timeout pressure, resolved by the 30s timeout bump 7de53d9; no state leak, no teardown bug) and JWE-29 (full audit of date/time coincidence with runtime defaults; all date literals in tests now use day-in-2..27, convention documented in §9). CLI, service layer, and GUI core functionality are complete.

**Roadmap.** v1.1.0 (target 2026-06-13) — GUI Etappe 6 (JWE-2) is complete: two-channel i18n model, full marker resolution, CLI --lang, runtime switch, persistence, 745 tests. Remaining for v1.1.0: security foundation (URL allowlist to *.atlassian.net JWE-22, bandit/pip-audit in CI JWE-23) and the CLAUDE.md German-residual cleanup (JWE-28). v1.2.0 (target 2026-06-27) — a purely visual redesign (epic JWE-32): a dark "Technical/Mono" theme, frameless window shell, and card-based section layout, on top of the existing PySide6 widget tree with no functional change. The earlier UX-polish items (inline-validation red border, minimum window size, ad-hoc QSS styling) are absorbed into JWE-32 and delivered there against the new design tokens rather than hand-rolled in v1.1.0 (JWE-3 -> JWE-36, JWE-4 -> JWE-34). v1.3.0 (target 2026-07-11) — User Management v2 (local SQLite cache, wildcard search, CSV/group import, presets; epic JWE-11) and the interaction redesign (replace the shuttle, multi-selects; epic JWE-12), built on the v1.2 theme.

**CI infrastructure.** GitHub Actions is the primary CI and the source of truth for releases (Windows builds are attached to GitHub Releases at `v*` tags). GitLab CI (`.gitlab-ci.yml`, Stufe 1: tests only) was added alongside the mirror to give GitLab-only collaborators independent verification of every push to `main` and every tag. GitLab CI has been fully green since JWE-10 (QRadioButton click compatibility fix for the winrm executor). The mirror push to GitLab is manual (never from Claude Code).

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
| `jwe.i18n` | ✅ implemented | Two-channel model: STRINGS + t(key, lang) for localized presentation; DIAGNOSTICS + diag(key) for English-only log/error messages. 97% coverage, 218 tests. |
| `jwe.cli` | ✅ implemented | argparse with export, discover-cloud-id, and gui subcommands, exit codes 0-6, tqdm progress bar, KeyboardInterrupt drain loop; --lang on export subcommand; errors via diag(), progress/summary via t(key, lang); 82% coverage, 19 tests |
| `jwe.gui` | ✅ etappen 1-5b + Etappe 6 complete | Full GUI implementation: AuthWidget with dual-mode panels, UserSearchWidget with debounced search, FilterWidget, OutputWidget, StatusWidget with progress + cancel + result buttons; ExportWorker and UserSearchWorker via Pattern C (persistent worker threads with lazy start); closeEvent confirmation; QSettings round-trip for all persistent fields; full i18n (two-channel model, runtime language switch, QSettings persistence). 745 tests green across the suite. Visual redesign (theme, frameless shell, cards) tracked as epic JWE-32 for v1.2.0. |
| `jwe.gui_main` | 🟡 etappe 1 (skeleton) | QApplication bootstrapper; 0% unit coverage (requires display) |

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
python -m jwe gui

# Build Windows binaries (also runs in CI)
pyinstaller jwe-cli.spec
pyinstaller jwe-gui.spec
```

`.spec` files for PyInstaller are not yet generated — create them on first build with `pyinstaller --onefile --name jwe-cli src/jwe/__main__.py` and edit afterward.

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
12. **`jwe.gui`** — last, because by this point all the building blocks exist. Use PySide6 (Qt6). Run the export in a `QThread` and post progress back to the main thread via Qt signals — never call UI widgets from a worker thread. See §14 for the detailed implementation roadmap.

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

---

## 10. Known traps (in priority order)

1. **Wrong base URL with service-account token** → 401 with no helpful message. Always go through `URLBuilder`.
2. **Missing `View All Worklogs` permission** → empty results, no error. Cross-check by counting issues found vs. worklogs returned and warn if the ratio looks suspicious.
3. **Scope-locked tokens** → 403 on specific endpoints only. Mode A error handler should mention this possibility.
4. **ADF with embedded mentions and inline cards** → naive text extraction loses the user reference. The fixture covers this.
5. **Pagination off-by-one** with `startAt`/`maxResults` (worklogs) vs. `nextPageToken` (search) — they're different APIs with different mechanisms.
6. **DE Excel and CSV encoding** — UTF-8 BOM is non-negotiable; without it, umlauts break in Excel DE.
7. **PySide6 main thread and workers** — never call Qt widgets from a worker thread. Use `QThread` + signals/slots; emit progress via custom signals only.

---

## 11. References

- PRD: `docs/PRD_Jira_Worklog_Exporter.md`
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
- **One-shot thread cleanup in auth.py:** `auth.py` lines ~345-346 still use `thread.finished.connect(worker.deleteLater)` + `thread.finished.connect(thread.deleteLater)`. This is a single-shot worker (not Pattern C), and the `deleteLater` chaining was identified as a crash trigger in the export worker (Commit 16e3af3). No crash has been observed here because these threads are short-lived and infrequent, but the pattern should be revisited and aligned with the safer approach used in the export worker. user_search.py was fixed to Pattern C in JWE-26; auth.py is tracked under JWE-6 for v1.1.
- **cancel_event granularity in run_export:** The cancel_event check in `jwe/exporter.py` is tested once per issue, not once per worklog page. For issues with very large worklog counts (hundreds of pages), a single iteration can take several seconds, meaning `closeEvent`'s `thread.wait(2000)` may expire before the export actually stops. Resolution: check cancel_event inside the worklog pagination loop as well. Tracked under JWE-7 for v1.1.

---

## 14. GUI implementation roadmap

Each etappe is one commit and is implemented in a fresh Claude Code session. The mandatory review pattern applies to every etappe — see end of this section.

### i18n-Marker convention (Etappen 2–5b)

Every hardcoded UI string (label text, button caption, placeholder, error message) that is not yet wired to `t()` must be annotated inline:

```python
self.label.setText("Connection test")  # i18n: auth.btn.test_connection
```

This makes the Etappe 6 refactoring mechanical (grep for `# i18n:`) rather than a hunt through the codebase.

v1.0.0 released after Etappe 5b; v1.0.1 followed as a patch. Etappe 6 is complete as of v1.1.0 (see below). The visual UX polish originally bundled with it (inline-validation styling, minimum window size, QSS theming) has been pulled into the v1.2 visual redesign epic JWE-32 — see "v1.2 — Visual redesign" at the end of this section.

### Two-channel i18n convention (established in Etappe 6, applies permanently)

**Logging and all error/failure messages are always English** (`DIAGNOSTICS` / `diag(key, **kwargs)`, no `lang` param). Only UI chrome — labels, buttons, titles, placeholders, dialogs, and CLI progress/summary — is localized (`STRINGS` / `t(key, lang, **kwargs)`). This keeps logs grep-able and troubleshooting single-language regardless of the user's selected locale.

Rule of thumb: if the string appears in a log file or in response to an error condition, use `diag()`. If the user reads it in the normal operating flow, use `t(key, lang)`.

The `test_no_i18n_markers_remain_in_src` test in `tests/test_i18n.py` gates regressions: any new hardcoded UI string that is not immediately wired through `t()` or `diag()` will cause CI to fail.

---

### ✅ Etappe 1 — Skeleton & Infrastruktur

**Goal:** Launchable window with the full structural frame; no real functionality yet.

**Implements:**
- `MainWindow(QMainWindow)` — Fusion style, orchestrator only
- Hybrid layout: `StatusWidget` anchored at the bottom, `QScrollArea` above containing `AuthWidget`, `UserSearchWidget`, `FilterWidget`, `OutputWidget` as empty `QGroupBox` stubs
- Language toggle button (🇩🇪 / 🇬🇧), `self._lang`, `language_changed` signal, `retranslate_ui(lang)` stubs on every widget
- `QSettings` save/restore for window geometry only

**Tests (pytest-qt):**
- `MainWindow` instantiates without error
- Language toggle flips `self._lang` and calls `retranslate_ui` on all section widgets
- QSettings geometry round-trip (save → restore)

---

### ✅ Etappe 2 — Auth Panel & Connection Test

**Goal:** Fully functional auth section; real Jira connection testable.

**Implements:**
- `ServiceAccountPanel` and `UserTokenPanel` as separate `QWidget` subclasses inside a `QStackedWidget`
- Radio buttons for mode switch (outside the stack, always visible)
- All auth fields: Cloud ID, service-account email, API token (masked), auth-header dropdown, site URL, email
- Cloud-ID-Discover dialog (site URL → async fetch via worker → fill Cloud ID field)
- Worker-based connection test (first use of `QThread` / `moveToThread` pattern)
- Keyring integration: auto-load token on startup, save-checkbox, graceful degradation (info label + disabled checkbox on `RuntimeError`)
- `QSettings` save/restore for all auth fields (not token)
- All strings marked `# i18n: <key>`

**Tests (pytest-qt):**
- Radio switch changes `QStackedWidget` index
- `ServiceAccountPanel` exposes exactly the SA fields; `UserTokenPanel` the user-token fields
- Connect button starts worker and emits signal (service mocked)
- `RuntimeError` from keyring → checkbox is disabled
- Token auto-filled on init when keyring returns a value

---

### ✅ Etappe 3 — User Search & Shuttle

**Goal:** User lookup and multi-selection fully operational.

**Implements:**
- `QLineEdit` + `QTimer` single-shot debounce (400 ms) triggering `search_users()` worker
- Left `QListWidget`: search results (displayName + email)
- Right `QListWidget`: selected users
- `→` / `←` arrow buttons; double-click shortcut on both lists
- Empty search term cancels pending timer, makes no API call
- All strings marked `# i18n: <key>`

**Tests (pytest-qt):**
- Debounce timer fires worker after delay (service mocked)
- Double-click on left list moves item to right list
- Arrow button moves selected items between lists
- Empty search string produces no worker start

---

### ✅ Etappe 4 — Filter, Output & Form Validation

**Goal:** Complete input form; export button correctly gated.

**Implements:**
- `FilterWidget`: `QDateEdit` from/to (default: current month), project keys `QLineEdit` (optional)
- `OutputWidget`: output directory `QLineEdit` + `QFileDialog` browse button, delimiter dropdown, column-profile dropdown, API-version dropdown
- Central validation: export button enabled only when ≥1 user selected and all required fields valid
- `QSettings` save/restore for: `auth_mode`, `cloud_id`, `service_account_email`, `site_url`, `email`, `auth_header`, `column_profile`, `delimiter`, `output_dir`, `api_version`, `lang`; **not** saved: `api_token`, `user_account_ids`, `from_date`, `to_date`
- All strings marked `# i18n: <key>`

**Tests (pytest-qt):**
- Export button disabled when no users in right list
- Export button disabled when date range is invalid
- Export button enabled when form is complete and valid
- QSettings round-trip for every persisted field

---

### ✅ Etappe 5a — ExportWorker & Progress Display

**Goal:** Export runs end-to-end; progress visible in UI.

**Implements:**
- `ExportWorker(QObject)` moved to `QThread` via `moveToThread`; consumes `service.run_export()` generator
- Signals: `progress_updated(int, int)`, `row_written()`, `export_finished(str)`, `error_occurred(str)`
- `StatusWidget` wired up: progress bar, issue/worklog counters, scrollable read-only log panel (last 50 lines)
- Export button triggers worker start; status panel becomes active
- All strings marked `# i18n: <key>`

**Tests (pytest-qt):**
- Worker emits `progress_updated` from mocked generator
- Worker emits `export_finished` with correct output path
- Worker emits `error_occurred` on exception from generator
- StatusWidget progress bar updates on `progress_updated` signal
- Log panel receives messages appended by worker

---

### ✅ Etappe 5b — Cancel, closeEvent & Result Actions

**Goal:** Safe cancellation, exit protection, post-export affordances.

**Implements:**
- Cancel button sets `threading.Event`; worker stops cleanly between generator yields
- Cancel button visible and enabled only during active export
- `closeEvent` checks for active export; shows `QMessageBox` confirmation before allowing close
- „CSV öffnen" / „Ordner öffnen" buttons appear after `export_finished`; use `QDesktopServices.openUrl`
- All strings marked `# i18n: <key>`

**Tests (pytest-qt):**
- Cancel button sets the `threading.Event`
- Worker exits loop after event is set
- `closeEvent` during active export triggers confirmation dialog (`QMessageBox` mocked)
- „CSV öffnen" button calls `QDesktopServices.openUrl` with correct path

---

### ✅ Etappe 6 — Full i18n (v1.1.0)

**Goal:** Fully internationalised GUI and CLI; runtime language switch; two-channel i18n model.

**Implements:**
- Two-channel i18n model in `jwe/i18n.py`: `STRINGS` + `t(key, lang)` for localized presentation; `DIAGNOSTICS` + `diag(key)` (no lang param) for English-only logs and error/failure messages
- All 72 `# i18n:` markers resolved across 7 files: `t()` everywhere for UI strings, `diag()` for log panel and error lines; zero markers remain in `src/`
- `retranslate_ui` bodies filled in on all five section widgets; `retranslate_ui` re-sets only `t()` strings (diagnostic/log strings do not change on language switch)
- `ExportProgress.message` field removed (was dead); `exporter.msg.*` keys dropped from all tables
- CLI: `--lang {de,en}` on `export` subcommand; errors via `diag()`, progress/summary via `t(key, lang)`
- Language persisted via `QSettings`; runtime toggle works across all presentation strings

**Tests (pytest-qt, 745 tests total):**
- STRINGS en/de parity; every key resolves via `t()` for both locales without `KeyError`
- Every DIAGNOSTICS key resolves via `diag()` without `KeyError`; no double-home with STRINGS
- Placeholder coverage: every `{param}`-bearing template tested with its documented kwargs
- Runtime switch: MainWindow starts in de, toggle updates section title, button, counter, placeholder to en equivalents; diagnostic strings confirmed identical before and after toggle
- Language persistence: toggle to en, close, reconstruct with same QSettings, assert en restored
- Marker-grep gate: `test_no_i18n_markers_remain_in_src` scans `src/` and asserts zero `# i18n:` markers; runs in CI on every push

> The inline-validation styling and minimum-window-size items that previously lived here moved to the v1.2 visual redesign (JWE-32): the error border is delivered as a token-based QSS class in JWE-36, the minimum window size is enforced by the frameless shell in JWE-34.

---

### v1.2 — Visual redesign (epic JWE-32)

A purely visual and structural re-skin on top of the existing PySide6 widget tree — no change to data flow, auth, export, CSV, or threading logic. Direction "Technical/Mono": navy base, cyan neon accent, monospace labels/numbers, bracketed section indices, card-based sections, terminal-style export log. The interactive prototype lives outside the repo (`JWE Redesign.html`); the prototype and the extracted token values should be committed under `docs/design/` before JWE-33 starts.

New architecture introduced here (all under `jwe/gui/`):
- `theme/tokens.py` — single source of truth for palette, spacing, radii, font roles (no Qt import)
- `theme/app.qss` — central stylesheet loaded once on QApplication startup; Fusion stays the base style
- `widgets/section_card.py` — reusable numbered card wrapping each of the four sections
- a frameless `MainWindow` (custom title bar with DE/EN toggle, min/max/close, window move) replacing OS chrome
- restyled form controls, identity strip + status chips, themed export footer, and a motion layer (`QPropertyAnimation`/`QTimer`/`QGraphicsDropShadowEffect`) with a reduced-motion fallback

Child stories: JWE-33 (tokens/theme), JWE-34 (frameless shell, absorbs JWE-4), JWE-35 (section cards), JWE-36 (form controls, absorbs JWE-3's error border), JWE-37 (identity strip/chips), JWE-38 (interim user/chip styling, pre-JWE-12), JWE-39 (export footer), JWE-40 (motion). Keep the auth-mode controls as `QRadioButton`s (styled as a segmented control) for winrm test compatibility per §9. Each story stays one Etappe = one commit = one session; §1 and this section are updated on completion.

### Review pattern (verbindlich für jede Etappe)

1. **Klassen-Skizze** — Klassennamen, Vererbungen, wichtigste Signals/Slots in Prosa vorab zeigen. Warten auf explizite Freigabe.
   Die Test-Liste in der Skizze muss zwei Regeln befolgen:
   - **Felder-Präsenz einzeln**: jedes UI-Feld bekommt einen eigenen Test (nicht „SA-Panel hat korrekte Felder" als einen Test).
   - **Gegenteil-Fälle einplanen**: zu jedem „A führt zu B"-Test auch „nicht-A führt nicht zu B" notieren (z.B. „Checkbox aus → save_token NICHT aufgerufen"). Das verdoppelt erfahrungsgemäß die Test-Zahl gegenüber der Erstschätzung.
2. **Code schreiben** — `# i18n: <key>` an jedem hardcodierten String (Etappen 2–5b), keine Doppler, Ruff- und mypy-konform.
3. **Tests grün + Sichtprüfung** — `pytest` läuft durch; das laufende Fenster wird kurz beschrieben (kein Screenshot-Test).
4. **Commit + Push + §1- und §14-Update** — CLAUDE.md §1-Statustabelle im selben Commit aktualisieren; zugleich den abgeschlossenen Etappen-Header in §14 auf ✅ setzen.
