# Brief — JWE-22 (URL allowlist) + JWE-23 (bandit + pip-audit in CI)

Security-foundation pair, both v1.1.0, children of JWE-13. Verified against origin/main @ 9624813.
Two independent commits. `git fetch origin; git pull origin main` first; ASCII commits, no
Co-Authored-By; mirror to GitLab manually after green GitHub CI.

---

## JWE-22 — URL allowlist to *.atlassian.net  (mostly DONE; close the gap)

**Finding: the control already exists and is applied everywhere.**
- `src/jwe/api/url_builder.py`: `_SITE_URL_RE = ^https://[a-z0-9][a-z0-9-]*\.atlassian\.net$` (re.IGNORECASE). `validate_site_url()` enforces it; `validate_cloud_id()` enforces the UUID for the Service-Account gateway host (`api.atlassian.com`, fixed).
- Applied at all three entry points: `config.py` (validation), `URLBuilder.for_auth` (UserToken path), and `api/tenant_info.discover_cloud_id` (validates BEFORE any request).
- `api/tenant_info.discover_cloud_id` uses `requests.get(..., allow_redirects=False)`, and `api/client.JiraCloudClient.request` also sets `allow_redirects=False` — so neither the discovery nor the authenticated path can be redirected to an off-allowlist host (no token-leak-via-redirect).
- Regex verified against bypass attempts: rejects `http://`, trailing slash, path, `acme.com`, bare `atlassian.net`, suffix `acme.atlassian.net.evil.com`, and userinfo `acme.atlassian.net@evil.com`. Accepts valid + case variants.

**The gap: adversarial negative tests are missing.** `tests/test_url_builder.py` covers empty / http / trailing-slash / path / wrong-domain / no-scheme, but NOT the two highest-risk bypasses. Lock them in so a future regex edit can't silently reopen them.

**Work:**
1. In `tests/test_url_builder.py`, add to the `test_validate_site_url_rejects_bad` parametrize list:
   - `"https://acme.atlassian.net.evil.com"`  (suffix attack)
   - `"https://acme.atlassian.net@evil.com"`  (userinfo attack)
   - `"https://acme.atlassian.net:8080"`      (port — currently rejected by the regex; lock the intent)
   - `"https://1.2.3.4"`                       (bare IP)
2. Mirror one suffix/userinfo negative case into `tests/test_tenant_info.py` so the discovery path's pre-request validation is explicitly covered against bypass (not just "Invalid site_url").
3. Add a one-line security-intent note to `url_builder.py` near `_SITE_URL_RE` and to the `allow_redirects=False` sites: "Security control (JWE-22): allowlist + no redirects; do not relax." So a future refactor doesn't loosen them unknowingly.
4. No production-code change to the validation itself — it is correct. Acceptance: new negative cases pass; full suite green.

(If a port like `:8080` should actually be ALLOWED for some reason, flag it — currently the regex rejects ports, which is the safer default.)

---

## JWE-23 — bandit + pip-audit in CI

Add SAST (bandit) and dependency-vulnerability scanning (pip-audit). Today CI runs ruff +
mypy + pytest only (GitHub `build-windows.yml`, GitLab `.gitlab-ci.yml`).

**Dependencies:** add to the `dev` extra in `pyproject.toml` so every CI job already installs them
(no install-line changes): `"bandit[toml]>=1.7"`, `"pip-audit>=2.7"`.

**bandit config** in `pyproject.toml`:
```
[tool.bandit]
exclude_dirs = ["tests"]
```
Run as `bandit -r src -c pyproject.toml`. Tests are excluded (asserts/B101 noise). Triage any
finding: fix, or add a scoped `# nosec <ID>  # reason` with justification — do not blanket-skip.

**pip-audit:** run `pip-audit` (audits the installed environment). It may flag transitive advisories
outside our control.

**CI placement (recommendation):** a single dedicated `security` job/step on ONE matrix leg
(Ubuntu / Python 3.12), not across the whole matrix — these scans are platform-independent, so
running them N times is waste.
- GitHub `build-windows.yml`: add a separate `security` job (ubuntu-latest, 3.12) that installs
  `.[dev]` and runs `bandit -r src -c pyproject.toml` then `pip-audit`.
- GitLab `.gitlab-ci.yml`: add a `security` stage/job mirroring it.

**Sub-decisions (pick; defaults in brackets):**
1. bandit severity gate: fail on [medium-and-up] vs only high. Medium-and-up is the sensible default.
2. pip-audit blocking: [blocking] with a documented `pip-audit --ignore-vuln <ID>` escape hatch for
   accepted/un-fixable transitive advisories — vs non-blocking (warn only). Blocking is the point of
   the task; the ignore-list keeps it from breaking CI on advisories we can't fix.

**Acceptance:** both scanners run in GitHub + GitLab CI on a push to main; a known-bad pattern (e.g.
`eval` of input) would fail bandit; the build stays green on the current clean codebase.

---

## Order & status
Independent; suggest JWE-22 first (small, closes the control's test gap), then JWE-23 (its bandit
scan then also covers the new code). JWE-22 is "In Progress"; JWE-23 flips to "In Progress" when it
starts. The versioning convention note for CLAUDE.md (from JWE-43) can ride along with whichever
commit touches docs, or wait for the JWE-28 sweep.
