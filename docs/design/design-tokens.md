# Jira Worklog Exporter — Design Tokens

**Direction:** Technical / Mono · **Ticket:** JWE-48 · **Consumed by:** JWE-33 (`jwe/gui/theme/tokens.py`, SSOT)

This is the human-readable token reference. Machine-readable values live in [`tokens.json`](./tokens.json). The interactive prototype is [`JWE Redesign.html`](./JWE%20Redesign.html); the Qt translation reference is [`QSS-Richtung.html`](./QSS-Richtung.html).

> **Canonical resolution.** Values below are *resolved* for the chosen **Mono** variant — the base `.jwe` tokens with `[data-variant="mono"]` overrides applied. Where any other file shows a lighter base value, **`tokens.json` wins** (the prototype is the source of truth).

---

## Colors

| Token | Value | Role |
|---|---|---|
| `color.bg.canvas` | `#060B13` | Canvas behind the window |
| `color.bg.window` | `#05090F` | Window / main background |
| `color.bg.card` | `#0A1019` | Section card / `QGroupBox` |
| `color.bg.card2` | `#0B121C` | Nested / secondary surface |
| `color.bg.input` | `#060C14` | Inputs, lists, log, progress track |
| `color.bg.inputFocus` | `#0C1826` | Input background on focus |
| `color.line.hairline` | `rgba(120,160,200,0.16)` | Default 1px border |
| `color.line.soft` | `rgba(120,160,200,0.08)` | Subtle dividers |
| `color.line.strong` | `rgba(126,166,206,0.22)` | Emphasized borders |
| `color.text.primary` | `#E9EFF7` | Primary text |
| `color.text.secondary` | `#93A4BA` | Secondary text |
| `color.text.tertiary` | `#5B6D82` | Hints / disabled |
| `color.accent.base` | `#22D3EE` | Neon accent |
| `color.accent.bright` | `#4EE6F7` | Accent hover |
| `color.accent.deep` | `#0E7C91` | Accent (avatars / gradients) |
| `color.accent.ink` | `#03171C` | Text/icon on accent fill |
| `color.status.ok` | `#34D399` | Success / connected |
| `color.status.warn` | `#FBBF24` | Warning |
| `color.status.err` | `#FB7185` | Error |

## Radii (Mono)

| Token | Value | Applies to |
|---|---|---|
| `radius.control` | `4px` | Inputs, buttons, small controls |
| `radius.card` | `6px` | Section cards |
| `radius.window` | `10px` | Window outer corner |

*Restrained baseline (not used in the chosen direction): control 8 / card 12 / window 16.*

## Spacing

| Token | Value |
|---|---|
| `space.windowPadding` | `22px` |
| `space.sectionGap` | `16px` |
| `space.fieldGap` | `14px` |
| `space.labelGap` | `6px` |
| `space.cardPadding` | `18px 20px 20px` |

## Typography

Two families:
- **Sans** — `"Segoe UI", "Helvetica Neue", Helvetica, Arial, system-ui, sans-serif`
- **Mono** — `"JetBrains Mono", ui-monospace, "SF Mono", "Cascadia Code", Menlo, monospace`

| Role | Family | Size | Weight | Notes |
|---|---|---|---|---|
| Body / field text | Mono | 12 | 400 | Mono variant. Base sans body = 13. |
| Section title | Sans | 15 | 600 | |
| Section subtitle | Sans | 11.5 | 400 | |
| Label | Mono | 11 | 600 | UPPERCASE · +0.08em |
| Value / IDs | Mono | 12 | 400 | |
| Log | Mono | 11.5 | 400 | line-height 1.7 |
| Counter (issues / WL) | Mono | 19 | 600 | tabular-nums |
| Counter label | Sans | 10 | 600 | UPPERCASE · +0.08em |
| Titlebar title | Mono | 12.5 | 500 | |
| Chip | Mono | 10.5 | 500 | UPPERCASE · +0.07em |

---

## Web → QSS translation notes

The prototype emits web HTML/CSS/JS; the target is PySide6/Qt with QSS — a **CSS subset**. Token *values* (colors, sizes, radii, families) port 1:1 into `tokens.py`. Layout and motion are rebuilt with Qt. Watch for:

| Web concept | Qt / QSS equivalent |
|---|---|
| `box-shadow` (focus ring, window shadow) | Not in QSS. Focus → `border: 1px solid #22D3EE`. Shadows → `QGraphicsDropShadowEffect`. |
| `letter-spacing` (uppercase mono labels) | Not in QSS. Use `QFont.setLetterSpacing(QFont.AbsoluteSpacing, n)`. |
| `text-transform: uppercase` | Not in QSS. Uppercase the string in code, or set on the label. |
| Neon glow (optional) | `QGraphicsDropShadowEffect(blurRadius=22, color=QColor(34,211,238,140), offset=0)` on primary button / section icons / connection chip. |
| Flex/grid layout | `QHBoxLayout` / `QVBoxLayout` / `QGridLayout`. |
| Indeterminate marquee progress | `QProgressBar` with range `(0, 0)`. |
| Scanline texture | Tiled `QPixmap` as widget background. |
| CSS transitions | `QPropertyAnimation`. |

See `QSS-Richtung.html` for the worked global stylesheet and per-widget guidance.
