# Jira Cloud Worklog Exporter (`jwe`)

CSV-Export von Worklogs einzelner Benutzer aus einer Jira-Cloud-Site — als CLI und kleine Tkinter-GUI, paketiert als Windows-Executable.

> **Status:** v0 / Skeleton. Architektonische Grundlagen (Auth, URL-Routing, Cloud-ID-Discovery) sind implementiert; Business-Logik wird sukzessive ergänzt. Siehe [`CLAUDE.md`](./CLAUDE.md) für den Implementierungsstand.

---

## Was es tut

Exportiert pro Lauf alle Worklogs einer Liste von Benutzern in einem Datumsbereich (optional eingegrenzt auf bestimmte Projekte) in eine CSV mit den Spalten **Projekt, Vorgangsschlüssel, Summary, Benutzer, Time Spent, Work Description**. UTF-8 mit BOM, streamend geschrieben — auch 100.000+ Zeilen sind kein Problem.

## Schnellstart (Entwicklung)

```powershell
git clone https://github.com/elementfortyseven/jira-worklog-exporter
cd jira-worklog-exporter
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
pytest
```

## Verwendung (sobald implementiert)

```powershell
# Service Account (bevorzugt)
$env:JWE_API_TOKEN = "..."
jwe-cli export `
  --auth-mode service-account `
  --cloud-id 1a11d016-8984-4c3e-b9ab-142dd06acb1b `
  --service-account-email jwe-bot@serviceaccount.atlassian.com `
  --token-env JWE_API_TOKEN `
  --users 5b10a2844c... `
  --from 2026-04-01 --to 2026-04-30 `
  --output-dir ./exports

# Personenbezogenes Token (Fallback)
jwe-cli export `
  --auth-mode user-token `
  --site-url https://acme.atlassian.net `
  --email me@example.com `
  --token-env JWE_API_TOKEN `
  --users 5b10a2844c... `
  --from 2026-04-01 --to 2026-04-30

# GUI starten
jwe-gui
```

## Voraussetzungen für den Service-Account-Modus

Siehe [PRD Anhang A](./docs/PRD_Jira_Worklog_Exporter.md#anhang-a-setup-anleitung-für-den-org-admin-service-account-modus) — der Org-Admin muss den Service Account anlegen, App-Access vergeben, Project-Permissions setzen und ein API-Token mit den richtigen Scopes erstellen.

**Read-only Scopes:** `read:jira-work`, `read:jira-user` (klassisch) oder die granularen Äquivalente.

## Dokumentation

- [PRD (vollständige Spezifikation)](./docs/PRD_Jira_Worklog_Exporter.md)
- [`CLAUDE.md`](./CLAUDE.md) — Entwicklerleitfaden, primärer Kontext für Claude Code

## Lizenz

MIT — siehe [LICENSE](./LICENSE).
