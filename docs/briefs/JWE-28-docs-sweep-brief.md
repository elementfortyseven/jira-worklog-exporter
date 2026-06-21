# Brief — JWE-28 documentation sweep

Docs/comments only. ONE commit, no code logic changes. `git fetch origin; git pull origin main`
first; ASCII commit message, no Co-Authored-By. Verified against origin/main @ 5dd62fa.

Scope is bigger than the issue's original list (which predates the doc-sync). Five parts:

---

## 1. "Etappe(n)" -> "Stage(s)" terminology migration

Global, case-preserving rename across `CLAUDE.md`, `src/`, and `tests/`:
`Etappe`->`Stage`, `Etappen`->`Stages`, `etappe`->`stage`, `etappen`->`stages`.
Plus `Infrastruktur` -> `Infrastructure` (the Stage 1 header).

The AC requires ZERO "Etappe" hits in src/ and tests/ too — not just CLAUDE.md.

- **CLAUDE.md** occurrences (verify by grep, do not trust line numbers): §0 "GUI Etappen workflow"
  header + body; §1 roadmap line and the `jwe.gui` / `jwe.gui_main` rows ("etappen 1-5b", "etappe 1");
  §14 intro, the "i18n-Marker convention (Etappen 2-5b)" header, the "Two-channel i18n convention
  (established in Etappe 6...)" header, all six `### ✅ Etappe N — ...` headers, and the JWE-32 section's
  "one Etappe = one commit" line.
- **src/** docstrings/comments: `gui/widgets/output.py`, `user_search.py`, `filter.py`, `status.py`
  (module docstrings), `gui/widgets/auth.py:440` (TODO "etappe 5b").
- **tests/** docstrings/comments: `test_status_widget_5a.py`, `test_status_widget_5b.py`,
  `test_main_window.py` (docstring + the "Etappe 4" comment), `test_main_window_5a.py`,
  `test_export_worker.py` (docstring + the "Etappe 5b" comment), `test_filter_widget.py`,
  `test_output_widget.py`, `test_auth_widget.py`.
- **Do NOT rename test file names** (`test_main_window_5a.py` etc. stay) — only the inner text
  "Etappe 5a" -> "Stage 5a". The `5a`/`5b` suffixes are fine.

## 2. Translate the German review-pattern block (CLAUDE.md §14)

The `### Review pattern (verbindlich für jede Etappe)` block is fully German. Replace with:

```
### Review pattern (mandatory for every stage)

1. **Class sketch** — present class names, inheritance, and the key signals/slots in prose first.
   Wait for explicit approval. The test list in the sketch must follow two rules:
   - **Field presence individually**: each UI field gets its own test (not "SA panel has the correct
     fields" as a single test).
   - **Plan negative cases**: for every "A leads to B" test, also note "not-A does not lead to B"
     (e.g. "checkbox off -> save_token NOT called"). In practice this roughly doubles the test count
     versus the first estimate.
2. **Write code** — `# i18n: <key>` on every hardcoded string (Stages 2-5b), no duplicates,
   ruff- and mypy-clean.
3. **Tests green + visual check** — `pytest` passes; the running window is briefly described
   (no screenshot test).
4. **Commit + push + §1 and §14 update** — update the CLAUDE.md §1 status table in the same commit;
   set the completed stage header in §14 to ✅.
```

## 3. §1 roadmap line — security foundation is DONE

The line still lists the security foundation as "Remaining for v1.1.0". Update so it reads (keep the
v1.2/v1.3 sentences): GUI Stage 6 (JWE-2) complete; **security foundation complete** — URL allowlist
to *.atlassian.net (JWE-22) and bandit/pip-audit in CI (JWE-23); **remaining for v1.1.0: README
refresh (JWE-41) and the JWE-6/JWE-7 housekeeping items.** (Once this commit lands, JWE-28 itself is
done, so do not list it as remaining.)

## 4. `jwe.i18n` §1 table row — test count

`... 97% coverage, 218 tests.` -> `... 97% coverage, 244 tests.` (244 confirmed via collect-only.)

## 5. New convention notes

**(a) Security tooling** — add a short note (in §9 / the CI area) documenting JWE-23, since its
"Documented in CLAUDE.md" AC was otherwise unmet: bandit + pip-audit run as a dedicated `security`
CI job (GitHub + GitLab, Ubuntu/3.12); `bandit -r src -c pyproject.toml -ll` gates at medium-and-above
severity; pip-audit is blocking, with `pip-audit --ignore-vuln <ID>` (documented in the workflow) as
the escape hatch for unfixable transitive advisories; suppress a bandit finding with
`# nosec <ID>  # reason` at the call site.

**(b) Versioning** — add a short note (from JWE-43): `__version__` in `src/jwe/__init__.py` is the
single source; pyproject derives it via hatchling. Bump the version only at release boundaries via a
`vX.Y.Z` tag (which triggers the Windows binary build + release); milestone/test builds use
pre-release tags (`vX.Y.Z-rc1`, published as GitHub pre-releases), never an ad-hoc bump.

---

## Acceptance

- `grep -rniE "Etappe|Skizze|Sichtpr|vollstaendig|vollständig|Vererbung|Infrastruktur|verbindlich|gruen|Fälle|Faelle|Präsenz|Praesenz" CLAUDE.md src/ tests/` returns nothing (CLAUDE.local.md is out of scope — German by preference).
- ruff, mypy, pytest still green (no logic touched, but run them).
- ASCII-only commit message.

## Out of scope
- `CLAUDE.local.md` (personal, German by preference).
- Past commit messages.
- The actual JWE-6 / JWE-7 *code* work — separate tickets (see the re-audit notes in chat).
