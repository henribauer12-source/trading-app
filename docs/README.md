# Documents

The specification is German. Code, identifiers and comments are English; everything the user
sees in the app is German.

**Precedence:** when two documents disagree, the one higher in this list wins. Do not silently
pick one — raise the conflict.

| # | File | What it governs | Status |
|---|---|---|---|
| 1 | `20260924_trading-app-qualitaetsstandards.md` | Security, dependency audit protocol, calculation-core rigour, look-ahead-bias rules, intraday data limits at 0 € | Binding for every phase |
| 2 | `20260925_rechenkern-spezifikation-v1.4.md` | Every trading/valuation formula, convention, cost and execution rule, the prediction engine (PE0–PE13), test catalogue T1–T40 with reference values and tolerances | v1.4 |
| 3 | `20260925_anlage-spezifikation.md` | **Core module "Anlegen"** (investment adviser): profile, equity share per goal, ETF selection, savings plan, rebalancing, overlays, German tax engine, projection, monthly recommendation, IPS, guardrails; tests TA1–TA22 | v1.3 |
| 4 | `20260925_strategie-katalog.md` | Every strategy as an exact rule plus its YAML definition, evidence grade, gates G1–G9, benchmarks, overlay variants OV-L2/OV-L4 | v1.2 |
| 5 | `20260925_trading-app-plan-v9.md` | Modules, architecture, UI information architecture, roadmap with phase gates | v9 |
| 6 | `20260924_trading-app-research.md` | Background evidence: tools, building blocks, media and expert signals, options | Context, not rules |

English reading copies: `20260925_anlage-spezifikation_en.md`, `20260925_trading-app-plan-v9_en.md`, `20260925_strategie-katalog_en.md`. The German originals are binding; change both together.

Working notes written during implementation (`20260925_bitemporale-datenschicht.md`, `20260925_instrument-stammdaten.md`, `20260925_intraday-datenquellen.md`, `20260925_rueckwirkende-anpassung.md`) explain decisions; they do not override 1–6. Superseded versions: `archive/`.

## Reading order for a newcomer

1. Plan v9 §1–§4 — what the app is and which modules exist; "Anlegen" is the core.
2. Quality standards — the rules that constrain everything else.
3. Spec v1.4 §1–§3 — conventions, point-in-time model, data layer.
4. Strategy catalogue — what actually gets computed and when it is allowed to show.

## Verification markers used throughout the spec

| Marker | Meaning |
|---|---|
| VERIFIZIERT | Checked against the primary source |
| UNVERIFIZIERT | Taken from secondary sources; **must** be checked before the module is implemented |
| ENTSCHEIDUNG | A deliberate choice, not a citation; the reasoning is given inline |

Spec v1.4 §11 and anlage spec A15 list the open points that must be closed before the corresponding module is built.
