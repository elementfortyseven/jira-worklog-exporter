# HISTORY.md — Jira Cloud Worklog Exporter

Archived project record. **Not** referenced via `@`-import from `CLAUDE.md`, so it
does not load into the Claude Code session context. Read on demand when you need the
release trail, the original build order, or the completed GUI-stage detail.

The live developer context is `CLAUDE.md`; the authoritative requirements are
`docs/PRD_Jira_Worklog_Exporter.md`.

---

## Release history

### v1.1.0 — released 2026-06-09

Shipped:
- GUI Stage 6 (JWE-2): two-channel i18n model with runtime language switch and CLI `--lang`; full marker resolution; 745 tests at release.
- Security foundation: URL allowlist to `*.atlassian.net` (JWE-22); bandit + pip-audit in CI (JWE-23).
- Version single-source-of-truth and pre-release tagging logic (JWE-43/44).
- README/docs refresh (JWE-41).
- Housekeeping JWE-6 / JWE-7 (see "Resolved backlog items" below).

Follow-ups resolved against `main` in this line:
- **JWE-31** — cold-start timeout flake, fixed by the 30s timeout bump (`7de53d9`); diagnosed as no state leak and no teardown bug.
- **JWE-29** — date/time coincidence audit; test date literals standardised to day-in-2..27 (the convention now in CLAUDE.md §9).

### v1.0.1 — released 2026-06-02

- **JWE-26** — UserSearchWorker Pattern C refactor (fixes crash on fast typing).
- **JWE-27** — keyring backend bundling fix (restores "Save token to keyring" in shipped binaries).
- **JWE-30** — defensive keyring exception handling: `pywintypes.error` is not an `OSError` subclass, so the catch was broadened to `except Exception` with `# noqa: BLE001`.

### v1.0.0

Released after GUI Stage 5b. First full CLI + GUI release. Stage-by-stage build detail is in "Completed GUI stages" below.

### Engineering notes carried out of these releases

- **PowerShell BOM/encoding** during version bump: `Set-Content` added a BOM and mangled a UTF-8 arrow. Future bumps use `[IO.File]::WriteAllText($path, $text, (New-Object Text.UTF8Encoding $false))`. (Now also recorded in CLAUDE.md §9.)
- **Two-instance MainWindow flaky tests** were skipped on Windows CI (`d0d1a0c`); the real fix landed as JWE-31.

---

## Original implementation order (all complete)

The build proceeded in this suggested order; every item below is implemented and green
(current coverage/test counts are in the CLAUDE.md §1 status table).

1. **Verify foundations.** Run `pytest tests/test_url_builder.py tests/test_auth.py` — must pass before touching anything else. *(This single rule is retained live in CLAUDE.md §7.)*
2. ✅ **`jwe.api.client`** — `connect()` and a generic `request()` using AuthStrategy + URLBuilder; retry on 429/5xx respecting `Retry-After`.
3. ✅ **`jwe.adf`** — pure `adf_to_text(adf_node) -> str`; built against the fixture file.
4. ✅ **`jwe.api.user`** — `search_users(query) -> list[User]` and `get_myself() -> User`.
5. ✅ **`jwe.api.search`** — `iter_issues(jql, fields) -> Iterator[IssueRef]` with `nextPageToken` pagination.
6. ✅ **`jwe.api.worklog`** — `iter_worklogs(issue_key, since, until) -> Iterator[Worklog]` with offset pagination.
7. ✅ **`jwe.config`** — dataclass capturing every CLI/GUI input; validation lives here.
8. ✅ **`jwe.csv_writer`** — context manager that opens the file, writes header, appends rows, flushes per row.
9. ✅ **`jwe.exporter`** — orchestrates the §4 data flow.
9.5. ✅ **`jwe.service`** — service layer consumed by both CLI and GUI. Wraps test_connection, search_users, discover_cloud_id, run_export, keyring-based token persistence, config_from_env. CLI and GUI import from here, not from exporter/user/tenant_info directly. `ExportConfig.build_auth()` was added so auth-strategy construction lives in exactly one place.
10. ✅ **`jwe.cli`** — argparse, env-var fallback, exit codes per PRD §11.
11. ✅ **`jwe.i18n`** — `t(key, lang, **kwargs)` with de/en tables, KeyError on unknown key, en fallback for unknown lang.
12. ✅ **`jwe.gui`** — PySide6 (Qt6). Export runs in a `QThread`; progress posts back via Qt signals; never call UI widgets from a worker thread. Detailed stage roadmap below.

---

## Completed GUI stages (Stages 1–6)

Each stage was one commit in a fresh session, under the review pattern still recorded in
CLAUDE.md §14. The permanent conventions (i18n-Marker, two-channel i18n, review pattern)
remain in CLAUDE.md; only the per-stage build records are archived here.

### ✅ Stage 1 — Skeleton & Infrastructure

Launchable window with the full structural frame; no real functionality.

Implemented:
- `MainWindow(QMainWindow)` — Fusion style, orchestrator only
- Hybrid layout: `StatusWidget` anchored at the bottom, `QScrollArea` above containing `AuthWidget`, `UserSearchWidget`, `FilterWidget`, `OutputWidget` as empty `QGroupBox` stubs
- Language toggle button (🇩🇪 / 🇬🇧), `self._lang`, `language_changed` signal, `retranslate_ui(lang)` stubs on every widget
- `QSettings` save/restore for window geometry only

Tests (pytest-qt):
- `MainWindow` instantiates without error
- Language toggle flips `self._lang` and calls `retranslate_ui` on all section widgets
- QSettings geometry round-trip (save → restore)

### ✅ Stage 2 — Auth Panel & Connection Test

Fully functional auth section; real Jira connection testable.

Implemented:
- `ServiceAccountPanel` and `UserTokenPanel` as separate `QWidget` subclasses inside a `QStackedWidget`
- Radio buttons for mode switch (outside the stack, always visible)
- All auth fields: Cloud ID, service-account email, API token (masked), auth-header dropdown, site URL, email
- Cloud-ID-Discover dialog (site URL → async fetch via worker → fill Cloud ID field)
- Worker-based connection test (first use of `QThread` / `moveToThread` pattern)
- Keyring integration: auto-load token on startup, save-checkbox, graceful degradation (info label + disabled checkbox on `RuntimeError`)
- `QSettings` save/restore for all auth fields (not token)
- All strings marked `# i18n: <key>`

Tests (pytest-qt):
- Radio switch changes `QStackedWidget` index
- `ServiceAccountPanel` exposes exactly the SA fields; `UserTokenPanel` the user-token fields
- Connect button starts worker and emits signal (service mocked)
- `RuntimeError` from keyring → checkbox is disabled
- Token auto-filled on init when keyring returns a value

### ✅ Stage 3 — User Search & Shuttle

User lookup and multi-selection fully operational.

Implemented:
- `QLineEdit` + `QTimer` single-shot debounce (400 ms) triggering `search_users()` worker
- Left `QListWidget`: search results (displayName + email)
- Right `QListWidget`: selected users
- `→` / `←` arrow buttons; double-click shortcut on both lists
- Empty search term cancels pending timer, makes no API call
- All strings marked `# i18n: <key>`

Tests (pytest-qt):
- Debounce timer fires worker after delay (service mocked)
- Double-click on left list moves item to right list
- Arrow button moves selected items between lists
- Empty search string produces no worker start

### ✅ Stage 4 — Filter, Output & Form Validation

Complete input form; export button correctly gated.

Implemented:
- `FilterWidget`: `QDateEdit` from/to (default: current month), project keys `QLineEdit` (optional)
- `OutputWidget`: output directory `QLineEdit` + `QFileDialog` browse button, delimiter dropdown, column-profile dropdown, API-version dropdown
- Central validation: export button enabled only when ≥1 user selected and all required fields valid
- `QSettings` save/restore for: `auth_mode`, `cloud_id`, `service_account_email`, `site_url`, `email`, `auth_header`, `column_profile`, `delimiter`, `output_dir`, `api_version`, `lang`; **not** saved: `api_token`, `user_account_ids`, `from_date`, `to_date`
- All strings marked `# i18n: <key>`

Tests (pytest-qt):
- Export button disabled when no users in right list
- Export button disabled when date range is invalid
- Export button enabled when form is complete and valid
- QSettings round-trip for every persisted field

### ✅ Stage 5a — ExportWorker & Progress Display

Export runs end-to-end; progress visible in UI.

Implemented:
- `ExportWorker(QObject)` moved to `QThread` via `moveToThread`; consumes `service.run_export()` generator
- Signals: `progress_updated(int, int)`, `row_written()`, `export_finished(str)`, `error_occurred(str)`
- `StatusWidget` wired up: progress bar, issue/worklog counters, scrollable read-only log panel (last 50 lines)
- Export button triggers worker start; status panel becomes active
- All strings marked `# i18n: <key>`

Tests (pytest-qt):
- Worker emits `progress_updated` from mocked generator
- Worker emits `export_finished` with correct output path
- Worker emits `error_occurred` on exception from generator
- StatusWidget progress bar updates on `progress_updated` signal
- Log panel receives messages appended by worker

### ✅ Stage 5b — Cancel, closeEvent & Result Actions

Safe cancellation, exit protection, post-export affordances.

Implemented:
- Cancel button sets `threading.Event`; worker stops cleanly between generator yields
- Cancel button visible and enabled only during active export
- `closeEvent` checks for active export; shows `QMessageBox` confirmation before allowing close
- „CSV öffnen" / „Ordner öffnen" buttons appear after `export_finished`; use `QDesktopServices.openUrl`
- All strings marked `# i18n: <key>`

Tests (pytest-qt):
- Cancel button sets the `threading.Event`
- Worker exits loop after event is set
- `closeEvent` during active export triggers confirmation dialog (`QMessageBox` mocked)
- „CSV öffnen" button calls `QDesktopServices.openUrl` with correct path

### ✅ Stage 6 — Full i18n (v1.1.0)

Fully internationalised GUI and CLI; runtime language switch; two-channel i18n model.

Implemented:
- Two-channel i18n model in `jwe/i18n.py`: `STRINGS` + `t(key, lang)` for localized presentation; `DIAGNOSTICS` + `diag(key)` (no lang param) for English-only logs and error/failure messages
- All 72 `# i18n:` markers resolved across 7 files: `t()` everywhere for UI strings, `diag()` for log panel and error lines; zero markers remain in `src/`
- `retranslate_ui` bodies filled in on all five section widgets; `retranslate_ui` re-sets only `t()` strings (diagnostic/log strings do not change on language switch)
- `ExportProgress.message` field removed (was dead); `exporter.msg.*` keys dropped from all tables
- CLI: `--lang {de,en}` on `export` subcommand; errors via `diag()`, progress/summary via `t(key, lang)`
- Language persisted via `QSettings`; runtime toggle works across all presentation strings

Tests (pytest-qt, 745 tests total at release):
- STRINGS en/de parity; every key resolves via `t()` for both locales without `KeyError`
- Every DIAGNOSTICS key resolves via `diag()` without `KeyError`; no double-home with STRINGS
- Placeholder coverage: every `{param}`-bearing template tested with its documented kwargs
- Runtime switch: MainWindow starts in de, toggle updates section title, button, counter, placeholder to en equivalents; diagnostic strings confirmed identical before and after toggle
- Language persistence: toggle to en, close, reconstruct with same QSettings, assert en restored
- Marker-grep gate: `test_no_i18n_markers_remain_in_src` scans `src/` and asserts zero `# i18n:` markers; runs in CI on every push

The inline-validation styling and minimum-window-size items originally bundled with Stage 6 moved to the v1.2 visual redesign (JWE-32): the error border is delivered as a token-based QSS class in JWE-36, the minimum window size is enforced by the frameless shell in JWE-34. (Live tracking in CLAUDE.md §14.)

---

## Resolved backlog items

- **JWE-6 — auth.py one-shot thread cleanup (resolved in v1.1.0):** closed after review — `auth.py`'s connection-test / cloud-id workers are genuinely one-shot, for which the `thread.finished → deleteLater` idiom is correct and is additionally hardened with explicit ref-clearing. The `16e3af3` GC race was specific to the long-lived/reused export worker (already on Pattern C). No code change warranted.
- **JWE-7 — cancel_event granularity in run_export (resolved in v1.1.0):** `jwe/exporter.py` now checks `cancel_event` inside the worklog pagination loop as well as between issues, so cancellation aborts within a single issue's worklog pages instead of only at the next issue boundary.
