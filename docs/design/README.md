# docs/design — Visual redesign source (v1.2)

Canonical design source for the **Technical / Mono** redesign. Landed per **JWE-48** as the precondition for **JWE-33** (`jwe/gui/theme/tokens.py`).

## Contents

| File | What it is | Status for JWE-33 |
|---|---|---|
| `tokens.json` | **Machine-readable tokens — the durable artifact.** | **Mirror this into `theme/tokens.py`.** |
| `design-tokens.md` | Human-readable token reference + Web→QSS map. | Read alongside `tokens.json`. |
| `JWE Redesign.html` | Interactive prototype (the visual spec). | Reference for layout / behavior. |
| `styles.css` | Prototype stylesheet — CSS-variable form of the tokens. | Where a value is unclear, this is the rendered truth. |
| `app-window.jsx`, `design-canvas.jsx` | Prototype React sources. | Support files for the prototype. |
| `QSS-Richtung.html` | Design→Code translation: worked QSS + per-widget Qt guidance. | Reference for the QSS build. |

## For JWE-33

1. Build `jwe/gui/theme/tokens.py` (no Qt import) from **`tokens.json`** — colors, radii, spacing, font roles, type scale.
2. Treat the **resolved Mono values** as canonical. The prototype wins over any lighter values shown elsewhere.
3. The export is a **visual spec, not transplantable code** — do not paste web CSS into `app.qss`. Port token *values* 1:1; rebuild layout with Qt layouts and motion via `QPropertyAnimation`. See the Web→QSS table in `design-tokens.md` / `QSS-Richtung.html`.

## Provenance

Direction produced/refined in Claude Design from the existing `JWE Redesign.html`. Docs-only — no code/CI impact. Updated 2026-06-19.
