# Jira Cloud Worklog Exporter (`jwe`)

CSV export of worklogs from a Jira Cloud site, filtered by users, date range, and optionally by projects. Available as CLI and PySide6 GUI, packaged as a standalone Windows executable (no Python required).

[![Release](https://img.shields.io/github/v/release/elementfortyseven/jira-worklog-exporter)](https://github.com/elementfortyseven/jira-worklog-exporter/releases/latest)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## Quick start (Windows)

1. Download the latest release from [Releases](https://github.com/elementfortyseven/jira-worklog-exporter/releases/latest):
   - `jwe-gui.exe` — graphical interface (recommended)
   - `jwe-cli.exe` — command line
   - `SHA256SUMS.txt` — checksums for verification
2. Double-click `jwe-gui.exe` or invoke `jwe-cli.exe` from PowerShell.

**Note on SmartScreen:** v1.0.0 is not code-signed. On first launch, Windows will display a SmartScreen warning. Click *More info* → *Run anyway*.

**Verify checksum (optional):**

```powershell
(Get-FileHash .\jwe-gui.exe -Algorithm SHA256).Hash
# Compare the value with SHA256SUMS.txt
```

---

## What the application does

Per run, all worklogs of the selected users within the given date range (optionally restricted to specific projects) are exported to a CSV file. Default columns: project, issue key, summary, user, time spent, work description. The file is streamed in UTF-8 with BOM — even large exports with over 100,000 rows work without memory issues.

Three column profiles are available: `minimal` (6 columns), `standard` (10 columns, default), `full` (14 columns — additionally account ID, worklog ID, creation and update dates).

---

## Authentication

The application supports two authentication modes.

**Service Account (recommended for regular exports)**
A dedicated, non-personal account with its own API token. Advantages: no token rotation when staff changes, clear audit trails, read-only scopes. Setup requires org admin rights — see [PRD Appendix A](./docs/PRD_Jira_Worklog_Exporter.md).

**User Token (for personal use)**
An API token bound to your own Atlassian account. Faster to set up, but exports run under your identity and stop working when your account is deactivated.

**Read-only scopes** in both modes: `read:jira-work`, `read:jira-user` (classic) or the granular equivalents.

---

## GUI usage

`jwe-gui.exe` opens a window with five sections:

1. **Authentication** — choose mode (Service Account or User Token), enter credentials, test connection. Token can optionally be stored in the Windows Credential Manager.
2. **User search** — search field for finding Atlassian accounts; add to the "selected" list by double-click or buttons.
3. **Filter** — date range (from/to) and optional project keys (e.g. `KAN, INFRA`).
4. **Output** — target directory, CSV delimiter, column profile, API version.
5. **Status & Export** — start the export, view progress, cancel, open the result file directly.

The GUI is available in German and English (switchable in the menu).

---

## CLI usage

```powershell
# Service Account
$env:JWE_API_TOKEN = "..."
jwe-cli export `
  --auth-mode service-account `
  --cloud-id 1a11d016-8984-4c3e-b9ab-142dd06acb1b `
  --service-account-email jwe-bot@serviceaccount.atlassian.com `
  --token-env JWE_API_TOKEN `
  --users 5b10a2844c... `
  --from 2026-04-01 --to 2026-04-30 `
  --output-dir .\exports

# User Token
jwe-cli export `
  --auth-mode user-token `
  --site-url https://acme.atlassian.net `
  --email me@example.com `
  --token-env JWE_API_TOKEN `
  --users 5b10a2844c... `
  --from 2026-04-01 --to 2026-04-30

# Discover the cloud ID for a site
jwe-cli discover-cloud-id https://acme.atlassian.net

# Launch the GUI from the CLI
jwe-cli gui

# Full help
jwe-cli --help
jwe-cli export --help
```

**Multiple users:** `--users` comma-separated (`5b10a2..., 712020:...`) or via file with `--users-file path/to/users.txt` (one account ID per line, `#` for comments).

**Exit codes:** `0` success, `1` authentication failed, `2` validation error, `3` API or connection error, `4` cancelled by user, `5` no permission, `6` unexpected error.

---

## Platform support

- **Windows 11 (x64):** primary target platform, GUI and CLI tested, prebuilt executables.
- **Linux / macOS:** CLI works (from source), GUI not officially verified. Installation see *Development* section.

---

## Development

Prerequisite: Python 3.12 or newer.

```powershell
git clone https://github.com/elementfortyseven/jira-worklog-exporter
cd jira-worklog-exporter
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
pytest
```

For your own builds of the executables, additionally `pip install -e ".[dev,build]"` and see `.github/workflows/build-windows.yml` for the PyInstaller invocations.

---

## Documentation

- [Product Requirements Document](./docs/PRD_Jira_Worklog_Exporter.md) — full specification, requirements, architecture, setup guides
- [CLAUDE.md](./CLAUDE.md) — developer guide, module overview, operating instructions

---

## License

MIT — see [LICENSE](./LICENSE).
