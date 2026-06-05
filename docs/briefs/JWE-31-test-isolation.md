# JWE-31 — Implementation Brief: GUI test isolation

| | |
|---|---|
| **Issue** | [JWE-31](https://cyberleptic.atlassian.net/browse/JWE-31) — *GUI test isolation: state leak between MainWindow instances + mock keyring* |
| **Status** | In Progress |
| **Target** | v1.1.0 |
| **Created** | 2026-06-04 |
| **Scope** | `tests/gui/conftest.py` and `tests/gui/test_main_window.py` only. **No production changes to `service.py`.** |
| **Baseline** | `main` at `d0d1a0c` (v1.0.1). Pull before starting. |

This brief is the source of truth for the work. The Claude Code session prompt is a pointer to this file, not a copy of it.

---

## Why this exists

v1.0.1 shipped two workarounds, not fixes:

1. Three two-instance `MainWindow` tests in `test_main_window.py` are skipped on `win32` (`d0d1a0c`) because they time out intermittently in *different* code paths between runs — `closeEvent` on one run, `ServiceAccountPanel.__init__` of the second window on another. Classic flaky signature.
2. `service.load_token` catches a broad `except Exception` (`95c1e1a`) to survive the real keyring backend throwing `pywintypes.error` (WinError 1312) on the GitLab winrm runner.

JWE-31 replaces both with proper test isolation. The `service.py` `except` narrowing is **explicitly out of scope** — it is a separate decision tied to JWE-24 (v1.4 security audit). Do not touch it.

## Guardrails (from CLAUDE.md — read §0 and §9 first)

- **Diagnosis discipline (§0):** No pattern-matching fixes for intermittent hangs. Wait for CI -> instrument -> decide after real data. This brief is built around that rule; do not shortcut it.
- **Fixture cleanup discipline (§9):** GUI fixtures are generator fixtures with explicit `w.close()` teardown; `stop_running_threads()` stops pending debounce timers before quitting threads.
- **Commits:** ASCII-only messages, English. Conventional-commit prefixes.
- **Sync:** This is a local Claude Code session. Pull first; the architectural reviewer may have pushed docs directly.

The work is **two strictly sequential phases**. Do not combine them into one commit or one CI run.

---

## Phase 1 — Mock the keyring backend (land and verify alone)

Add an autouse fixture in `tests/gui/conftest.py`:

```python
@pytest.fixture(autouse=True)
def mock_keyring(monkeypatch):
    monkeypatch.setattr(
        "jwe.service.keyring.get_password",
        lambda *a, **kw: None,
        raising=False,
    )
```

Before writing it, **confirm the patch target resolves.** Since JWE-27 moved `keyring>=25.0` into the `[dev]` extra, `keyring` is installed in the test env, so `jwe.service.keyring` is the real module and `.get_password` exists. `raising=False` covers the degraded case where the optional import fell through and the alias is `None`.

**Preserve the keyring contract.** The autouse fixture mocks *every* GUI test. The handful of tests that specifically exercise `load_token` / keyring integration must still validate the real contract — give them an explicit override (a fixture that installs a controllable fake with known return/raise behavior, overriding the autouse one). This is an acceptance criterion, not optional.

**Do not** touch the state-leak tests or un-skip the three `win32` tests in this phase.

Commit alone, push to GitHub, let the **full CI matrix** run.

- **Expectation:** the `WinError 1312` / `pywintypes.error` failure class disappears on GitLab winrm, and the apparent flakiness of the geometry tests may drop.
- **Cut point — stop and report CI results before Phase 2.** If the keyring mock alone would make the three skipped tests reliably green, that is a useful signal — but **do not** assume the state leak is solved. Phase 2 still diagnoses from real data.

Suggested message: `test(gui): mock keyring backend in conftest autouse fixture (JWE-31)`

---

## Phase 2 — Diagnose the state leak, then fix at the right layer

### Step 1 — Instrument, do not guess

- Add `faulthandler.dump_traceback_later(<timeout>)` around the suspect tests so a hang dumps **all thread stacks** instead of an opaque `qtbot` timeout.
- Add targeted logging/markers at the three observed suspects: `stop_running_threads` (entry/exit, and the `quit()`+`wait()` result per thread — auth, user-search, export), `MainWindow.closeEvent` (before/after `super().closeEvent`), `ServiceAccountPanel.__init__` (entry).
- Temporarily un-skip the three two-instance tests **on a throwaway branch**, run them in isolation, repeatedly, on CI. Capture a real stack from an actual hang on the winrm runner.

### Step 2 — Decide by the captured stack

- **If the stack shows real teardown nondeterminism** — a thread whose `wait()` does not complete inside the timeout, or a pending debounce `QTimer` that still fires after `close()` -> **fix at the fixture/`closeEvent` layer (Option B).** Harden the teardown contract so all timers are stopped before `quit()` and `wait()` either completes deterministically or the test surfaces the failure clearly. **This is the preferred outcome** — the teardown contract also runs in production on every window close.
- **If the stack shows teardown completes cleanly** and the hang is pure GC/QSettings timing between two objects that never coexist in production -> **collapse the test to a single instance with explicit `save`/`load` (Option A).** The two-instance scenario was a test artifact; the contract under test is the QSettings round-trip, which does not need overlapping lifetimes.

### Step 3 — Keep the contract coverage (regardless of A or B)

Retain at least one test that explicitly asserts the teardown contract: after `close()`, no running `QThread`s and no active `QTimer`s on the widget. Do not lose the coverage that flaked.

### Step 4 — Remove the workaround

Remove the three `@pytest.mark.skipif(... win32 ...)` markers from `test_main_window.py` (`d0d1a0c`). They must pass un-skipped now.

### Step 5 — Clean up

Remove the Phase-2 instrumentation (`faulthandler`, debug markers) once the fix is in — unless a marker is worth keeping as a permanent assertion (Step 3 candidate).

---

## When to stop and consult the architectural reviewer

- After Phase 1 CI results, **before** starting Phase 2.
- After the instrumented stack is captured, **before** building the fix, **if** the stack points to something outside the A/B dichotomy — e.g. a genuine production bug in `closeEvent`. That is an architecture decision; escalate rather than patch.

## Acceptance criteria (JWE-31)

- GUI tests pass 100% across the full matrix (GitHub Actions Linux + Win 3.12/3.13, GitLab Win 3.12/3.13) over **at least 5 consecutive runs**.
- No production changes to `service.py`.
- Keyring-contract tests still validate the contract via explicit override.
- The three previously-skipped tests are un-skipped and green.

## Out of scope

- `service.py` `except` narrowing (JWE-24).
- Anything beyond `conftest.py` + `test_main_window.py` (plus the teardown-contract test from Step 3).

## CLAUDE.md updates required (maintenance discipline, §0)

- §1: test count / phase paragraph if they change.
- §9: add the teardown-contract assertion convention **if** one emerges from Step 3.
- Note JWE-31 resolution and which option (A or B) the stack drove, with a one-line rationale.
