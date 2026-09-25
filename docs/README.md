# Documents

The specification is German. Code, identifiers and comments are English; everything the user
sees in the app is German.

**Precedence:** when two documents disagree, the one higher in this list wins. Do not silently
pick one — raise the conflict.

| # | File | What it governs | Status |
|---|---|---|---|
| 1 | `20260924_trading-app-qualitaetsstandards.md` | Security, dependency audit protocol, calculation-core rigour, look-ahead-bias rules, intraday data limits at 0 € | Binding for every phase |
| 2 | `20260925_rechenkern-spezifikation-v1.4.md` | Every formula, convention, cost and execution rule, the prediction engine (PE0–PE11), test catalogue T1–T40 with reference values and tolerances | v1.4 |
| 3 | `20260925_strategie-katalog.md` | Every strategy as an exact rule plus its YAML definition, evidence grade, gates G1–G9, benchmarks | — |
| 4 | `20260925_trading-app-plan-v8.md` | Modules, architecture, UI information architecture, roadmap with phase gates | v8 |
| 5 | `20260924_trading-app-research.md` | Background evidence: tools, building blocks, media and expert signals, options | Context, not rules |

## Reading order for a newcomer

1. Plan v8 §1–§4 — what the app is and which modules exist.
2. Quality standards — the rules that constrain everything else.
3. Spec v1.4 §1–§3 — conventions, point-in-time model, data layer.
4. Strategy catalogue — what actually gets computed and when it is allowed to show.

## Verification markers used throughout the spec

| Marker | Meaning |
|---|---|
| VERIFIZIERT | Checked against the primary source |
| UNVERIFIZIERT | Taken from secondary sources; **must** be checked before the module is implemented |
| ENTSCHEIDUNG | A deliberate choice, not a citation; the reasoning is given inline |

Spec v1.4 §11 lists the open points that must be closed before the corresponding module is built.
