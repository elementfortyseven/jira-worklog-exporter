# Brief — JWE-43 (version SSOT) + JWE-44 (pre-release builds)

Two small, independent Housekeeping tasks (children of JWE-42), both v1.1.0. They touch
different files, so order does not matter; can be one commit or two. Pure config/build —
`git fetch origin; git pull origin main` first; ASCII commit message, no Co-Authored-By.

---

## JWE-43 — Version single source of truth (correct to 1.0.1)

Today three values disagree: `pyproject.toml` 1.0.0, `src/jwe/__init__.py` 0.1.0, released 1.0.1.
Make `__init__.py` the one source and let hatchling derive the package version from it
(binary-safe: a hardcoded constant resolves inside the frozen PyInstaller .exe, unlike
`importlib.metadata`).

**Edit 1 — `src/jwe/__init__.py`:**
```
OLD:  __version__ = "0.1.0"
NEW:  __version__ = "1.0.1"
```

**Edit 2 — `pyproject.toml`, `[project]` table:** remove the static version line and declare it dynamic.
```
OLD:  version = "1.0.0"
NEW:  dynamic = ["version"]
```

**Edit 3 — `pyproject.toml`, add a hatch version source** (anywhere in the `[tool.hatch...]` area; create if absent):
```
[tool.hatch.version]
path = "src/jwe/__init__.py"
```

(Note: with `dynamic = ["version"]`, hatchling reads `__version__` from the file in Edit 3.
Do not leave both a static `version =` and `dynamic = ["version"]` — that is an error.)

**Verify:**
- `python -c "import jwe; print(jwe.__version__)"` -> `1.0.1`
- `pip install -e ".[dev]"` succeeds; `python -m build` (or `hatch version`) reports 1.0.1
- existing test suite still green (mypy / ruff / pytest no-args)

---

## JWE-44 — Mark pre-release tags as GitHub pre-releases

The `build-windows` job already builds on any `v*` tag (incl. `v1.1.0-rc1`). This only labels
the resulting GitHub release so an rc build is not shown as "Latest".

**Edit — `.github/workflows/build-windows.yml`, the "Upload to Release" step.** Add one line to its `with:` block:
```
OLD:
      - name: Upload to Release
        uses: softprops/action-gh-release@v2
        with:
          files: |
            dist/jwe-cli.exe
            dist/jwe-gui.exe
            dist/SHA256SUMS.txt

NEW:
      - name: Upload to Release
        uses: softprops/action-gh-release@v2
        with:
          prerelease: ${{ contains(github.ref_name, '-') }}
          files: |
            dist/jwe-cli.exe
            dist/jwe-gui.exe
            dist/SHA256SUMS.txt
```

Semver pre-release tags always contain a hyphen (`v1.1.0-rc1`, `v1.1.0-beta1`) and release
tags never do, so `contains(github.ref_name, '-')` is the correct discriminator.

**Verify (after merge to main):** pushing `v1.1.0-rc1` builds the two .exe + SHA256SUMS and
creates a GitHub *pre-release*; a later `v1.1.0` creates a normal release.

---

## After both land

Cut a pre-release to test the build end-to-end:
```
git tag -a v1.1.0-rc1 -m "v1.1.0-rc1: i18n milestone build"
git push origin v1.1.0-rc1
```
CI builds the binaries and publishes them as a pre-release. Reserve the clean `v1.1.0`
tag for the real release once the rest of the v1.1.0 scope (JWE-22/23 security, JWE-28) lands.

The versioning convention goes into CLAUDE.md at the next docs touch:
"Version bumps only at release boundaries via a `vX.Y.Z` tag (which triggers the binary
build); milestone/test builds use pre-release tags (`vX.Y.Z-rc1`), never an ad-hoc bump."
