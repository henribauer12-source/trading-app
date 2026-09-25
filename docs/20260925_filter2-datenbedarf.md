# Filter 2 — what data is needed, and what the pull already showed

Status: research note, not yet a spec change. Feeds A5.5 and `hard_filters._INDICES_A5_5`.
Retrieved 2026-09-25. Every value below is UNVERIFIZIERT until confirmed against the
fund document itself (the ranking of A5.1 applies: KID > annual report > prospectus >
factsheet; provider websites and justETF rank below all of these and count as a lead,
never as a source).

## Summary

The pull answered the question it was meant to answer, and turned up a design fault
that is larger than the missing data.

**Filter 2 compares the index name exactly (`frozenset.__contains__`). Real documents
do not use the spellings in A5.5.** This is not a gap in the two open blocks — it
already misfires on the two blocks that are implemented:

| Spelling | Verdict today | Where this spelling comes from |
|---|---|---|
| `MSCI ACWI` | fulfilled | A5.5 |
| `MSCI ACWI Index (Net)` | **violated** | how iShares writes it on the factsheet |
| `FTSE All-World` | fulfilled | A5.5 |
| `FTSE All-World Index` | **violated** | usual spelling |
| `€STR` | fulfilled | A5.5 |
| `ESTR Compounded` | **violated** | Amundi Smart Overnight Return (LU1190417599) |
| `Solactive €STR +8.5 Daily Total Return` | **violated** | Xtrackers II EUR Overnight Rate Swap (LU0290358497) |

A correct fund is rejected because of a suffix. Decide this before filling in the
missing four blocks, otherwise the same fault is inherited four more times.

## Per block

### K1 Global equities — spellings needed
A5.5 is right on substance; only the spelling is short. Observed: `MSCI World Index (Net)`
for the MSCI World leg (iShares Core MSCI World, IE00B4L5Y983). The `(Net)` suffix is the
net-total-return variant and is the normal case for UCITS ETFs — it is the index *variant*,
not a different index.

Pull: exact `Benchmark Index` line from the KID of one fund per permitted index.

### K2 Money market — a rate is not an index
`€STR` is the ECB's overnight rate, not a tradable index. No ETF can track it directly;
they track a compounded index derived from it (`ESTR Compounded`) or a swap index with a
spread (`Solactive €STR +8.5 Daily Total Return`, the +8.5 bp being the swap spread).
A5.5 must name the derived indices, or filter 2 must accept "€STR-based".

Pull: KID benchmark line for LU1190417599 and LU0290358497.

### K2 EUR government bonds — EGBI confirmed, bands confirmed
FTSE Russell's own EGBI factsheet confirms A5.5 exactly: the parent index and the bands
`1-3`, `3-5`, `5-7`, `7-10`, `10+ Years` all exist as published sub-indices with their own
figures (par amount, average life, effective duration). A5.5's maturity bands are sound.

Effective duration per band, for the A4.1 horizon match: 1-3y → 1.89, 3-5y → 3.78,
5-7y → 5.54, 7-10y → 7.42, 10+ → 13.97. Parent EGBI → 6.89, average life 9.50y.
Source: FTSE Russell EGBI factsheet (research.ftserussell.com), figures undated in the
extract — **as-of date must be read off the PDF before any of this is stored.**

Open: which ETFs actually track the *bands* rather than the parent. The search surfaced
only parent-index and climate-variant funds. A band-level ETF may not exist in UCITS form,
in which case A4.1's maturity matching cannot be implemented with EGBI band ETFs and needs
a different instrument (e.g. iShares/Amundi euro-govvie funds on their own band indices).

Pull: for each band, does a UCITS ETF exist, and what is its benchmark spelling.

### K2 Global bonds — hedging is part of the index name
Confirmed that the EUR-hedged variant is a named index, not a fund property:
`Bloomberg Global Aggregate Bond Index (EUR hedged)` (SPDR SPFE). Unhedged funds name
`Bloomberg Global Aggregate Bond Index` (iShares AGGH IE00BD1JRY91 — note AGGH is the
hedged share class but the website still prints the unhedged index name, so the website
cannot be trusted here). Vanguard uses a different index entirely:
`Bloomberg Global Aggregate Float Adjusted and Scaled Index in EUR`.

Two consequences: hedging must be checked on the index name, not only the `currency_hedged`
field; and "Global Aggregate" covers at least three non-identical indices.

Also noted: SPDR's index changed name on 2022-02-01 (Bloomberg Barclays → Bloomberg).
Historical documents carry the old name. A name check against older documents needs
the alias.

Pull: KID benchmark line for one hedged and one unhedged Global Aggregate fund.

### S-Gold — no index, and an open contradiction
Gold ETCs have no index; they have a reference price. A5.5 already says this correctly
(`LBMA Gold Price PM`, ICE Benchmark Administration, 15:00 London, USD auction price).
Filter 2 therefore cannot be an index check for S-Gold — it has to check the reference
price and the delivery claim (`gold_etc_delivery_claim` already exists as a field).

Unresolved: Xetra-Gold is described by a data vendor as tracking LBMA Gold Price PM
**in EUR per ounce**, while A5.5 states LBMA's euro prices are indicative only and the
USD auction price is the real one. Either the vendor is loose with wording or the ETC
uses the indicative euro print. This must be read in the Xetra-Gold Wertpapierprospekt,
not from a vendor page.

### S-Factor — A5.5 names an index that no ETF tracks
The clearest finding. A5.5 says `MSCI World Quality`. These are two different MSCI indices:

| Index | MSCI code |
|---|---|
| MSCI World Quality Index | 702787 |
| MSCI World Sector Neutral Quality Index | 705169 |

Both ETFs on this factor track **705169**: iShares Edge MSCI World Quality Factor
(IE00BP3QZ601, benchmark printed as `MSCI World Sector Neutral Quality Index (Net)`) and
Xtrackers MSCI World Quality 1C (`... (TRN)` in its KID). The Xtrackers *fund* is called
"Quality" while its *index* is "Sector Neutral Quality" — which is likely how the wrong
name entered A5.5.

The difference is real, not cosmetic: 705169 picks quality stocks *within each GICS sector*,
so sector weights stay near the parent. Unconstrained 702787 does not. A5.5's stated
selection criteria (ROE, stable earnings growth, low leverage) match 705169's published
description (high ROE, low leverage, low earnings variability) — so the *intent* is
705169 and only the name is wrong.

Recommendation: correct A5.5 to `MSCI World Sector Neutral Quality`. This is a factual
correction, but it changes which products pass, so it is yours to confirm.

## What to pull, precisely

For each fund below, from the **KID** (PRIIPs), falling back to the prospectus:
the benchmark index line verbatim, the document's as-of date, and the retrieval URL.

| Block | ISIN | Why this one |
|---|---|---|
| K1 | IE00B4L5Y983 | MSCI World leg, spelling reference |
| K1 | — | one MSCI ACWI and one FTSE All-World fund still to pick |
| K2 money market | LU1190417599 | `ESTR Compounded` |
| K2 money market | LU0290358497 | `Solactive €STR +8.5` |
| K2 EUR govt | — | one per maturity band, if they exist |
| K2 global bonds | IE00BD1JRY91 | hedged/unhedged naming conflict |
| S-Gold | DE000A0S9GB0 | Xetra-Gold, EUR/USD reference price question |
| S-Factor | IE00BP3QZ601 | confirm `Sector Neutral` |

## Decisions needed before this can be coded

1. **Exact match or normalised match.** Recommendation: normalise (strip the
   `Index`/`(Net)`/`(TRN)`/`UCITS` noise, case- and whitespace-fold) and match against a
   canonical index plus its known aliases, rather than a raw string set. Exact matching
   is currently producing false rejections, which is the dangerous direction for a filter
   that decides what may be bought.
2. **Index variant.** Is `(Net)` vs `(Gross)` vs `(TRN)` part of the identity, or noise?
   Recommendation: noise for matching, but recorded — net-return is the correct default
   for a German investor and gross would overstate returns.
3. **S-Gold** cannot use an index check; needs its own rule.
4. **S-Factor** name correction (see above).
5. **EGBI bands** may have no tradable ETF; A4.1 then needs a fallback.
