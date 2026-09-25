# Instrument master data for ETF selection

**Date:** 2026-09-25
**Status:** implemented and verified (commit `ac25960`); code identifiers translated to English in `81995d5` and `4b1c713`
**Specification:** investment specification v1.4 (`20260925_anlage-spezifikation_en.md`), A5.1 and A5.2 (additions of v1.3 and v1.4 not yet independently reviewed)
**Code:** `src/trading_app/instruments.py`, `src/trading_app/hard_filters.py`, `src/trading_app/sources/documents.py`
**Tests:** `tests/test_instruments.py`, `tests/test_hard_filters.py`, `tests/test_documents.py` — 266 green together with the rest of the suite

---

## What this covers

The data layer that A5 will later use for product selection: TER, tracking difference, fund size
and the other characteristics of ETFs and ETCs, plus the hard filters of A5.2. Not included:
scoring A5.3, index choice A5.4, product switch A5.6, and real ISINs.

## Design: one row per field value

A5.1 requires provenance **per field**: the TER comes from the February KID, the fund size from
the August factsheet. So the layer uses a narrow table `instrument_fields` with one row per value:
`isin, field, period, value, unit, source_url, source_type, status, as_of, retrieved_at, ingested_at`.

- A new field is an entry in `FIELDS`, not a schema migration.
- Annual values (tracking difference) are rows with a `period`, not one column per year.
- `value` is stored as text and converted in Python to `Decimal`, `bool`, `date` or a choice
  value. A DuckDB `DECIMAL` column was rejected: it rounds silently (measured: `0.12345678901` →
  `0.1235` in `DECIMAL(18,4)`), and `.df()` turns it into `float64`.
- A wide table with one column per field was rejected too: for provenance it would need four
  companion columns per field, or one row per document, which again allows only one as-of date.

## Time axes

| Column | Role as in `bars` | Meaning |
|---|---|---|
| `as_of` | `event_time` | date of the document |
| `retrieved_at` | `available_at` | from when the app knew the value; the point-in-time key |
| `ingested_at` | `ingested_at` | when the row was written |

When several values are known, the latest `as_of` applies; for equal `as_of`, the later retrieval.
A retrieval before the as-of date is rejected, both in Python and as a CHECK in the table
(compared in UTC). The KID precedence of spec v1.4 is not implemented yet (decision 4 below).

`as_of` also names the cut-off date of a query. See the known defect at the end.

## Unverified values

Every check in `check_hard_filters` ends as *fulfilled*, *violated* or *open*
(`Verdict.FULFILLED`, `Verdict.VIOLATED`, `Verdict.OPEN`). A missing or `UNVERIFIED` value
(`VerificationStatus`) gives *open*, and the product is then not eligible (`FilterResult.eligible`
is false). This is not an exception, because one unchecked value would then abort the evaluation of
every candidate. It is not a mere warning either, because a warning would let the product through.

## Legal limits in the code

There is no scraper. Values come from a hand-maintained JSON file (`load_source_file`; the format
is in the module docstring). `sources/documents.download_document` downloads exactly one PDF. It
accepts only https addresses whose path ends in `.pdf` and that have no query. An address whose
host has a label starting with `justetf` or `vanguard` is rejected before any connection is made,
also when it is a redirect target.

The source file belongs in the repo, because it should be versioned, but **not in `data/`**: that
path is in `.gitignore`.

## Mutation testing

Each sabotage ran in a fresh copy of `src/` and `tests/` with `PYTHONDONTWRITEBYTECODE=1` (see
`wiki/python-pyc-invalidation.md`), so the working tree stayed untouched. A control run without a
mutation gave 0 red tests. The table was measured on the German code base, before the translation.

| # | Sabotage | red |
|---|---|---|
| M1a | PIT filter removed (`field()`/`series()`) | 9 |
| M1b | PIT filter removed (`isins()`) | 3 |
| M2a | Cut-off `<=` → `<` (`field()`/`series()`) | 2 |
| M2b | Cut-off `<=` → `<` (`isins()`) | **0**, 1 after a new test |
| M3 | Fund-size filter 100m → 10m | 4 |
| M4 | History filter 3 → 1 year | 2 |
| M5a | Domain blocklist empty | 13 |
| M5b | Redirect check removed | 1 |
| M6a | `Decimal` → `float` on storing | 2 |
| M6b | `float` accepted as input | 1 |
| M6c | Source file read as `float` instead of `Decimal` | 4 |
| M7 | `UNVERIFIED` passes silently | 4 |
| M8 | Precedence ignores the as-of date | 1 |
| M9 | K1/money-market threshold 500m → 100m | 3 |
| M10 | Retrieval before the as-of date allowed | 1 |
| M11 | ISIN check digit ignored | 1 |
| M12 | Second-hand value may be `VERIFIED` | 1 |
| M13 | "Not on Xetra" → violated instead of open | 1 |
| M14 | Annual value before year end allowed | 1 |
| M15 | Duplicate check on append removed | 1 |
| M16 | Inception on 1 January not counted | 2 |
| M17 | Gold checks UCITS instead of the delivery claim | 1 |
| M18 | Table CHECK retrieval ≥ as-of date removed | **0**, 2 after a new test |
| M19 | Table CHECK without UTC conversion | 2 |

Result: 24 sabotages, all caught in the end. Two went unnoticed at first:

- the first run found M2b;
- the independent review found M18.

A test was added for each, and both are now caught. M19 shows only on a machine east of UTC (here
Europe/Berlin); on a UTC machine this mutation behaves exactly like the original.

## Decisions of 20260925 (spec v1.4)

These four items were open here until 20260925. They are now decided and written into the spec.

1. **Filter 2 for bonds, gold and factor: starting indices** (A5.5). K2 EUR government bonds: FTSE
   EMU Government Bond Index (EGBI), all maturities or one of its bands 1–3 / 3–5 / 5–7 / 7–10 / 10+
   years; the bands are why it was chosen. K2 global bonds: Bloomberg Global Aggregate, EUR-hedged.
   S-Gold: LBMA Gold Price PM, set by ICE Benchmark Administration at 15:00 London; the USD price
   is the auction price, LBMA's euro prices are indicative only. S-Factor: MSCI World Quality
   (return on equity, stable year-over-year earnings growth, low financial leverage).
   **Code not yet updated:** `hard_filters._INDICES_A5_5` still lists only K1 and K2 money market,
   so filter 2 stays *open* for the other four building blocks, and its reason still says that
   A5.5 names only an index family.
2. **Age measure: full calendar years everywhere** (A5.3). The history score now counts like
   A5.2 no. 4, not "years since inception". Reason: tracking difference is published per calendar
   year, so the history score must count the years for which a usable TD value exists.
   `full_calendar_years` already implements the count; scoring A5.3 is not built yet, so no code
   contradicts the decision.
3. **Fund size in a foreign currency: converted, with USD as the primary reporting currency**
   (A5.1, A5.2 on 3). The value is stored as published. It is converted into EUR at the rate of
   the value's own `as_of` date, never at today's rate, because otherwise a stored fund size would
   silently change on every re-run. Rate source: the ECB euro foreign exchange reference rates
   (free, daily). The rate is stored as a value with its own provenance, like every other value.
   **Specified, not yet implemented; this is a behaviour change.** `FIELDS["fund_size"]` still has
   unit `EUR` and `FieldValue` rejects any other unit. The ECB rate has no ISIN, so it does not fit
   `instrument_fields` as it stands; where it is stored is a design question for the
   implementation. The known defect below must be fixed first.
4. **TER conflict: the KID wins over the factsheet** (A5.1). Reason: the KID is mandated by the
   PRIIPs Regulation, with a prescribed calculation method and issuer liability; the factsheet is
   marketing material. When the two disagree, both values are stored, the KID value as `VERIFIED`
   and the factsheet value as a second entry, so the disagreement stays visible instead of being
   silently resolved. The same precedence applies to every other field that appears in both
   documents. **Not yet implemented:** `InstrumentView._current` ranks by
   `as_of DESC, retrieved_at DESC, row_id DESC` whatever the `source_type`, so today a later
   factsheet beats an earlier KID.

## Still open in the specification

1. **Spelling of the index:** for A5.3 ("same index") the variant (net/gross, currency, hedging)
   must be unambiguous. v1.3 fixed the A5.5 spelling only for K1 and the money market. The v1.4
   starting indices need it too, including the names of the EGBI maturity bands.
2. **Fund size, remaining questions:** does the fund's volume count, or the share class's? Which
   rate applies when the as-of date has no ECB rate (weekend, TARGET holiday)? The strategy
   catalogue G4 carries the last rate forward; doing the same here would be consistent.
3. **KID precedence against other documents:** the decision names the factsheet. Spec v1.4 gives
   the KID precedence over every other document, so that the ranking stays a total order. KID
   (February), annual report (June) and factsheet (August) would otherwise form a cycle.
4. **Closure announcement:** A5.6 treats it as a violation of a hard filter, but A5.2 has no filter
   for it.
5. **Replication "synthetic, multiple counterparties":** A5.3 gives 75 points only with
   *transparent collateral*. How to score a fund with several counterparties and no transparent
   collateral is open.
6. **"Low frequency" (A5.1):** there is no number, and the download enforces no rate limit.
7. **Filter 7 (savings-plan-eligible, P15):** user-specific, not part of this layer.
8. **TA16 against A5.2 no. 4:** TA16 still expects the hard filters to exclude funds that are "too
   young", but A5.2 no. 4 (v1.3) and the code label them `new` instead of excluding them.

## Known defect: `as_of` names two different dates

**Not fixed. Recorded 20260925; no code was changed.**

The translation mapped two distinct German concepts to the one English name `as_of`:

- ***Stand***, the date the document itself carries: `FieldValue.as_of`, the column
  `instrument_fields.as_of`, the source-file key `"as_of"`, and the "as of …" in each check's
  reason. Before the translation this was `stand`.
- ***Stichtag***, the cut-off date a query asks about: `FilterResult.as_of` (was `stichtag`).
  `InstrumentView.as_of` and `InstrumentStore.view(as_of=…)` already used `as_of` for the cut-off
  before the translation (German docstring: "Der Stichtag dieser Sicht"), and so do
  `PointInTimeView.as_of` and `BitemporalStore.view(as_of=…)` in `bitemporal.py`.

In a point-in-time store these are different axes. The document date orders the known values
(precedence); the cut-off date filters on `retrieved_at`. At the moment only a comment keeps them
apart (`instruments.py` module docstring: "Careful: the column `as_of` is the document date.
`InstrumentView.as_of` is the view's cut-off date").

Why it matters now: the currency conversion (decision 3) must use the rate of the value's
document date. With one name for both dates, a rate looked up at `value.as_of` and a rate looked up
at `view.as_of` look equally plausible. The second would re-price every stored fund size with each
new cut-off, which is exactly what the rule forbids.

**Proposed fix:** keep `as_of` for the document's own date; rename the query cut-off to `cut_off`.

- `InstrumentView.as_of` → `InstrumentView.cut_off`; `InstrumentStore.view(as_of=…)` →
  `view(cut_off=…)`; `FilterResult.as_of` → `FilterResult.cut_off`.
- For one vocabulary across the data layer, also `PointInTimeView.as_of` →
  `PointInTimeView.cut_off`, `BitemporalStore.view(as_of=…)` → `view(cut_off=…)`, and the
  parameter `full_calendar_years(…, cutoff)` → `cut_off`.
- A pure rename with no behaviour change. The cut-off mutants (M2a, M2b) must still go red
  afterwards. Do it before the currency conversion is implemented.
