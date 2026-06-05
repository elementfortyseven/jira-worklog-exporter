# JWE-31 Phase 2 — Implementation Brief: MainWindow state-leak diagnosis

| | |
|---|---|
| **Issue** | [JWE-31](https://cyberleptic.atlassian.net/browse/JWE-31) — Phase 2 |
| **Status** | In Progress |
| **Predecessor** | Phase 1 merged (`00e7fdc`) + timeout addendum (`7de53d9`). CI green on both platforms. |
| **Baseline** | current `main`. Pull before starting. |
| **Approach** | **Local-first.** Feature branches trigger neither GitHub Actions (push to `main` / tags / PR-to-`main` only) nor GitLab (`main` / tags only), so a throwaway branch gets no CI feedback. The diagnosis runs on the local Windows machine; CI is the final gate, reached by merging to `main`. |

---

## Goal

Resolve the three two-instance `MainWindow` tests in `tests/gui/test_main_window.py` that were skipped on `win32` in `d0d1a0c`. End state: the three tests pass un-skipped, reliably, across the full CI matrix.

## Critical reframing — do Step 1 before assuming a state leak exists

The original flaky signature was a timeout that moved between runs (`closeEvent` one run, `ServiceAccountPanel.__init__` of the second window another). Phase 1 proved that exact signature — a wandering timeout location — was **cold-start timeout pressure** under the old tight `10s` / `func_only=false` budget, not a logic bug, for the `auth_widget` case.

A two-instance test builds two full Qt widget trees sequentially, i.e. roughly double the construction cost, which made it the most exposed test under a 10s budget. With the timeout now at `30s`, there is a real chance these three tests simply pass. **Test that cheap hypothesis first. Do not instrument or touch production code until Step 1's result is in.**

## Guardrails (CLAUDE.md — read §0 and §9 first)

- **Diagnosis discipline (§0):** evidence before theory. This is why Step 1 precedes instrumentation, and instrumentation precedes any fix. No pattern-matching.
- **Fixture cleanup discipline (§9):** generator fixtures with explicit `w.close()` teardown; `stop_running_threads()` stops timers before quitting threads.
- ASCII-only commit messages, English. Pull first.

## Code facts to anchor the work (from current `main`)

- `MainWindow.closeEvent` stops three thread groups, each with a **bounded** `wait(2000)`: `auth_widget.stop_running_threads()` (`_conn_thread`, `_disc_thread`), `user_search_widget.stop_running_threads()`, and `_export_thread` (`quit()` + `wait(2000)`). A bounded wait that expires logs a warning and continues — it does **not** hang. So an indefinite hang cannot come from these waits alone.
- `_export_thread` is created and `moveToThread`'d in `__init__` but **started lazily** on first export. The `__init__` comment explicitly flags the danger: a running `QThread` GC-destroyed without a `closeEvent` (e.g. a window held only in a local variable and never closed) hangs at `__del__` time. This is the prime *real* candidate if Step 1 still flakes.
- The `make_main_window` factory fixture (conftest) shares **one** `isolated_settings` across every window it creates and closes them in creation order at teardown. The two-instance geometry round-trip (w1 writes geometry on close, w2 restores it) is what these tests actually assert.

---

## Step 0 — Setup (local)

Pull `main`, branch locally, confirm the 30s timeout is active. (Commands are in the session prompt, not here.)

## Step 1 — Test the "it was just the timeout" hypothesis

- Un-skip the three `@pytest.mark.skipif(... win32 ...)` tests in `test_main_window.py` (locally, for now).
- Run **only those three** under high repetition on the local Windows machine — e.g. 100x — with coverage disabled for speed and `-s` to surface any Qt warnings (notably `QThread: Destroyed while thread is still running`).
- Outcome:
  - **Reliably green over the full repetition** -> the original flake was timeout pressure, now resolved by the `30s` addendum. Go straight to Step 4 (remove skips permanently, add the teardown-contract assertion, done). No instrumentation, no A/B fix. **Report this before proceeding** — it likely closes Phase 2.
  - **Still hangs or flakes** -> proceed to Step 2.

## Step 2 — Instrument (only if Step 1 still flakes)

- Add `faulthandler.dump_traceback_later(<timeout>)` so a hang dumps **all** thread stacks (pytest-timeout's own dump is a fallback).
- Add temporary markers (logged, visible with `-s`):
  - `MainWindow.closeEvent`: before/after each `stop_running_threads()` call, and `_export_thread.isRunning()` + the `wait()` return value.
  - each widget `stop_running_threads()`: per-thread `isRunning` / `quit()` / `wait()` result.
  - `ServiceAccountPanel.__init__` entry (the prior wandering hang location — confirm whether it is real construction time or just where the sampler landed).
- Reproduce under repetition, capture a real hang stack to a log file.

## Step 3 — Decide by the captured stack (B over A)

- **Real teardown nondeterminism** — a `QThread` destroyed while running (the `_export_thread` GC scenario, or a window not closed before destruction), or a genuine deadlock -> **Option B: fix the teardown contract.** Ensure every instance's persistent threads are quit+joined before destruction, and that no code path can GC-destroy a running `QThread`. **Preferred** — it also fixes a real production close path.
- **Pure GC/QSettings timing between two instances that never coexist in production** -> **Option A: collapse to a single instance with explicit `save`/`load`.** The two-instance overlap was a test artifact; the contract under test is the QSettings round-trip.

## Step 4 — Finalize (all paths)

- Keep at least one test that asserts the teardown contract: after `close()`, `_export_thread.isRunning()` is `False` and the auth/user-search threads are stopped. Don't lose the coverage that flaked.
- Remove the three `skipif(win32)` markers permanently.
- Remove all Step-2 instrumentation unless a marker is worth keeping as a permanent assertion.

## Step 5 — Validate

- Local: the three tests green under repetition (target the JWE-31 bar: 100% over many runs, no retries).
- Then merge to `main` for the full matrix incl. GitLab Windows. Confirm the three un-skipped tests pass across the matrix over **>=5 consecutive runs**.

---

## Scope

- **In scope for Phase 2 (unlike Phase 1):** production teardown code — `MainWindow.closeEvent`, widget `stop_running_threads()`. Option B is expected to touch these; that is desirable.
- **Out of scope:** the `service.py` broad `except` narrowing (JWE-24).

## CI fallback (only if local will not reproduce)

- GitHub Actions Windows: open a PR to `main` (the `pull_request` trigger runs the `test` job). Caveat: GitHub's Windows runner has a primary user token and runs `offscreen`, so it may not reproduce a non-interactive-session effect.
- GitLab Windows (winrm): temporarily add `- if: $CI_PIPELINE_SOURCE == "web"` to the `workflow:rules` in `.gitlab-ci.yml`, push the branch to the GitLab mirror, run a manual ("web") pipeline, then revert the rule.

## Escalate to the architectural reviewer

- After Step 1, with the repetition result (it decides whether Phase 2 is essentially done or needs Steps 2-4).
- After the Step-2 stack is captured, before building the fix, if it reveals a genuine production teardown bug (e.g. a real path where a running `QThread` can be GC-destroyed without `closeEvent`) — that is a production correctness issue beyond the test and warrants a decision.

## CLAUDE.md updates required at JWE-31 resolution (§0 maintenance discipline)

- §1: test count / phase paragraph (the three tests move from skipped to passing).
- §9: the teardown-contract assertion convention from Step 4.
- One-line resolution note: which outcome held — "timeout artifact, resolved by 30s bump", or Option A, or Option B — with rationale.
