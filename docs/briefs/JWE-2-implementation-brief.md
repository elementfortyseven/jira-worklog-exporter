# JWE-2 Implementation Brief — Complete i18n marker resolution + runtime language switch

Verified against GitHub `main` @ `0cd155b` (clone + grep, not from memory).

## Current state (what already exists vs. what is missing)

**Exists and works:**
- `src/jwe/i18n.py`: `t(key, lang="en", **kwargs)` with en-fallback and `KeyError` on total miss. ~38 keys grouped `error.* / progress.* / summary.* / label.* / button.* / status.*`.
- Runtime-switch plumbing in `src/jwe/gui/main_window.py`: `language_changed = Signal(str)`, `self._lang` (default `"de"`), a flag-emoji toggle button (`lang_btn` -> `_toggle_language`), persistence of `"lang"` via `QSettings`, and `_retranslate_all(lang)` dispatching `retranslate_ui(lang)` to all five section widgets.
- Every section widget already declares `def retranslate_ui(self, lang: str)`.

**Missing (this is the work):**
- **`t()` has no real call site anywhere in `src/`** — only the docstring example imports it. The whole i18n layer is unused scaffolding today, CLI included.
- All `retranslate_ui` bodies are empty (docstring only).
- **72 `# i18n: <key>` markers** across 7 files still hold hardcoded literals: `main_window.py`, `widgets/auth.py`, `widgets/filter.py`, `widgets/output.py`, `widgets/status.py`, `widgets/user_search.py`, `exporter.py`.
- Hardcoded strings are **mixed-language** (e.g. `"Discover"`, `"Browse..."` English; `"Export laeuft"`, `"Abbrechen"`, `"CSV oeffnen"`, `"Abbruch wird durchgefuehrt..."` German) — all must route through `t()`.
- The marker keys use a **different namespace** than the current table (see Decision 1).

## Decisions to lock before coding

**1. Key namespace (LOCKED).** Markers use a granular, widget-scoped scheme that is NOT in the current table:
`app.title`, `section.{auth,filter,output,user_search}.title`, `auth.sa.label.*` / `auth.user.label.*` / `auth.*.placeholder`, `auth.radio.*`, `auth.checkbox.save_token`, `auth.btn.*`, `auth.status.*`, `auth.keyring.unavailable`, `filter.label.*` / `filter.project_keys.placeholder`, `output.label.*` / `output.btn.browse` / `output.delimiter.{comma,semicolon}` / `output.browse_dialog.title`, `user_search.*`, `status.btn.*` / `status.label.*` / `status.counter.{issues_n,worklogs_n}` / `status.log.*`, `dialog.close_during_export.{title,text}`, `exporter.msg.{cancelled,complete}`.
-> Adopt this granular scheme as the canonical key set. Add **every marker key** to `STRINGS` in both `en` and `de`. The pre-existing generic `label.*` / `button.*` keys are unused by the markers — see Decision 2.

**2. Two channels: diagnostics (English-only) vs presentation (localized) (LOCKED).** Logs AND error/failure messages stay English across both locales, so logs are grep-able and troubleshooting is single-language. Everything the user reads/operates in normal flow is localized. The generic `label.* / button.*` keys are unused leftovers -> **remove them**. Full key partition + mechanism in the dedicated section below ("Diagnostics vs presentation").

**3. Placeholders.** These keys take `{}` params; convert the current f-strings to `t(key, lang, ...)`:
- `status.log.export_complete` `{path}` ; `status.log.error` `{message}`
- `auth.status.connected` `{display_name}` `{email}` ; `auth.status.cloud_id_found` `{cloud_id}` ; `auth.status.discovery_failed` `{message}`
- `status.counter.issues_n` `{n}` ; `status.counter.worklogs_n` `{n}` (appear at 4 sites in `status.py`)

## Diagnostics vs presentation (two-channel model) — LOCKED

Two string sources in `i18n.py`:
- **`STRINGS`** (existing): `t(key, lang)`, de/en, parity-tested. **Presentation** — chrome + success/info + progress + summaries.
- **`DIAGNOSTICS`** (new): English-only dict, accessor `diag(key, **kwargs)` with no `lang` param. **Logs + errors/failures.** Shared by GUI and CLI so the same English text is reused, not duplicated.

Rule: logs and any error/failure message use `diag()`. Everything read/operated in normal flow uses `t(key, lang)`. Cancellation is NOT an error (see below).

**Move these 13 keys STRINGS -> DIAGNOSTICS (drop their `de` variants):**
- errors/failures: `error.api_failed`, `error.auth_failed`, `error.generic`, `error.permission_denied`, `error.unexpected`, `error.validation`, `auth.status.discovery_failed`, `auth.keyring.unavailable`
- GUI activity-log lines (the whole `log_panel` is English): `status.log.error`, `status.log.export_complete`, `status.log.dry_run_complete`, `status.log.cancelled`, `status.log.cancelling`

**Stay in STRINGS (localized):** all `section.*`, `*.label.*`, `*.placeholder`, `*.btn.*` / `status.btn.*`, `status.label.*`, `status.counter.*`, the status-state words `status.ready/connecting/exporting/done/cancelled`, `auth.status.connected/cloud_id_found/testing`, all `dialog.*`, all `progress.*`, all `summary.*` (CLI progress + summary are localized per the boundary decision), `exporter.msg.complete`.

**Cancellation (Point-1 decision):** the GUI log lines `status.log.cancelling/cancelled` are English (part of the log -> DIAGNOSTICS); the UI status-label state `status.cancelled` and the CLI summary line `summary.cancelled` stay localized.

**Cancellation keys — RESOLVED (do in 6c):** `error.cancelled` is already dropped (6a-fix). The remaining issue is `exporter.msg.cancelled` / `exporter.msg.complete`: verified that `ExportResult.message` is read by NO consumer (the CLI summary is built from the numeric result fields, the GUI builds its own `status.log.*` lines). So the `message` field is dead and the two keys are dead. Fix in 6c: remove both `exporter.msg.*` keys from the table, remove the two `# i18n:` markers in `exporter.py` (this clears the last markers ahead of the 6d grep gate), and remove or blank the unused `message` field on `ExportResult` (blank if a test asserts on it, else drop it). Do NOT keep `exporter.msg.cancelled` in DIAGNOSTICS — that split is the smell.

**Test:** keep the STRINGS en/de parity test; add a guard that no `DIAGNOSTICS` key also appears in `STRINGS` (no double-home), and that `diag()` has no `lang` parameter / ignores locale.

## Per-widget implementation shape

Import `t`; build text at construction with `t(key, lang)`; re-set the same text in `retranslate_ui(lang)`. Most target widgets are already stored as `self.<x>`. Widgets need the current lang at construction — pass `MainWindow.self._lang` into each ctor (or default + rely on the existing post-build `_retranslate_all`; confirm call order in `main_window.__init__`).

Fiddly bits to flag explicitly:
- **QGroupBox titles** set via `super().__init__("Authentication", ...)` -> retranslate with `self.setTitle(t("section.auth.title", lang))`.
- **QFormLayout row labels** (`layout.addRow("Site URL", field)`) are not stored. To retranslate, create the label explicitly: `lbl = QLabel(t(...)); layout.addRow(lbl, field); self._lbl_site_url = lbl`. This is the main mechanical change in `auth.py` / `filter.py` / `output.py`.
- **QComboBox data items** (`addItem(", (Comma)", ",")`) -> retranslate via `setItemText(i, t(...))` while preserving `itemData`.
- **Counters** ("Issues: 0" / "Worklogs: 0" at 4 sites) -> single keys with `{n}`, replace all sites.
- **Window title** via `setWindowTitle(t("app.title", lang))`; **QMessageBox** dialog title/text via the `dialog.*` keys.

## CLI i18n workstream (full CLI in scope)

`src/jwe/cli.py` (435 lines) has **zero `# i18n:` markers** and many hardcoded user-facing strings. In scope for JWE-2:

**Wire through `t()` (runtime messages):**
- Error lines: `error: {exc}`, `error: authentication failed - {exc}`, `error: permission denied - {exc}`, `error: API error - {exc}`, `error: unexpected error - {exc}` -> map onto the existing `error.auth_failed` / `error.permission_denied` / `error.api_failed` and add `error.unexpected` (+ a generic `error.generic`).
- `validate_overrides` `ValueError` texts (`use either --token or --token-env, not both`, `use either --users or --users-file, not both`, `cannot read users-file: {exc}`) -> `error.validation`-family keys.
- Progress: `tqdm(desc="Exporting", ...)` -> `progress.*`.
- Summary in `_print_summary` (`Output: {path}`, complete / cancelled lines) -> `summary.*` (mostly already present).
- `Authenticated as: {display_name} (accountId: {account_id})` -> new key.
- Mark each newly wired string with `# i18n: <key>` so the acceptance grep stays meaningful.

**Out of scope - keep English:** argparse `description=` / `help=` text. Help is built at parser-construction time, before any `--lang` is parsed (chicken-and-egg), and English CLI help is the convention for dev tools. Flagged so this is a deliberate choice, not an omission.

**CLI language source (recommendation):** `--lang` currently exists only on the `gui` subcommand. Add `--lang {de,en}` to `export` and `discover-cloud-id` (default `DEFAULT_LANG` = `en`) and thread it into the message calls. Preferred over env-detection for explicitness and parity with the `gui` flag. Flagging as a sub-decision; veto if you'd rather read it from an env var.



## Test strategy (pytest-qt)

- **Table integrity** (parametrized): every key in `en` exists in `de` and vice versa — no drift.
- **Key resolution**: collect every key referenced in code; assert `t(key, "de")` and `t(key, "en")` resolve without `KeyError`.
- **Marker gate**: assert `grep -r "# i18n:" src/` returns nothing after the change (this is JWE-2's acceptance criterion; can be a test or a CI step).
- **Runtime switch**: build `MainWindow`, capture representative texts (a group-box title, a button, a placeholder, a counter), call the toggle, assert each changed and equals `t(key, "en")` vs `t(key, "de")`.
- **Persistence**: toggle sets `QSettings["lang"]`; reconstruction with that `QSettings` restores it (reuse existing `save/load_settings`).

## Scope / commit granularity (your call)

72 GUI strings + 2 exporter + the full CLI pass is a large single Etappe. Suggested split within Etappe 6:
- **6a** — DONE (883904b): added all keys (en+de), removed generic `label./button.` keys, table-integrity tests.
- **6a-fix** — split the table: move the 13 diagnostic keys `STRINGS -> DIAGNOSTICS` (drop `de` variants), add `diag()` + the no-double-home / no-`lang` guard test. Small commit, do this first now that 6a shipped with everything in `STRINGS`. (1 commit)
- **6b** — GUI: wire `t()` (presentation) and `diag()` (log_panel + error lines); fill `retranslate_ui` bodies; replace the literals; QFormLayout label refs. Note: `retranslate_ui` re-sets only `t()` text — `diag()`/log lines do not change on language switch. (1 commit, or per-widget)
- **6c** — CLI: `--lang` plumbing; route errors through `diag()`, progress/summary through `t(key, lang)`; resolve the cancellation-key consolidation; mark new strings. (1 commit)
- **6d** — tests (parity, key resolution, runtime switch, persistence, diagnostics guard) + marker-grep gate; update CLAUDE.md §1/§14 + add the "logging/errors are English-only" convention (Etappe 6 -> done).

Flagging because the one-Etappe-one-commit convention would otherwise produce a very large single diff.

## Locked decisions (2026-06-06)

- Granular marker namespace is canonical; every key added in `en` + `de`; redundant generic `label./button.` keys removed.
- **Two-channel i18n**: `DIAGNOSTICS` (English-only, `diag()`) for logs + errors/failures; `STRINGS` (`t(key,lang)`) for presentation. CLI: `--lang {de,en}` on `export`/`discover-cloud-id` (default `en`) drives localized progress/summary; CLI errors and all logs stay English. argparse help/description stays English. 13 keys move STRINGS -> DIAGNOSTICS (see partition above).
- Commit split 6a (done) / 6a-fix / 6b / 6c / 6d as above.
