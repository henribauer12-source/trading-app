"""Index identity: normalisation, variant extraction, alias matching (A5.2 no. 2, v1.7).

RED first — the module does not exist yet.
"""

from __future__ import annotations

import datetime as dt

import pytest

from trading_app.index_identity import (
    Alias,
    Hedging,
    IndexRegistry,
    MatchVerdict,
    ReturnVariant,
    parse_index_name,
)
from trading_app.hard_filters import BuildingBlock
from trading_app.instruments import SourceType


# --- normalisation: decoration is dropped, identity is not -------------------


@pytest.mark.parametrize(
    "raw,canonical",
    [
        # The real spellings that v1.6 rejected.
        ("MSCI ACWI Index (Net)", "msci acwi"),
        ("MSCI ACWI", "msci acwi"),
        ("MSCI ACWI Index", "msci acwi"),
        ("msci acwi index (net total return)", "msci acwi"),
        ("MSCI ACWI (TRN)", "msci acwi"),
        ("FTSE All-World Index (Price)", "ftse all-world"),
        # €STR spelling variants: the ECB writes €STR, providers write ESTR.
        ("€STR", "estr"),
        ("ESTR", "estr"),
        ("€STR Index", "estr"),
        # Whitespace and separators providers vary freely.
        ("  MSCI   ACWI  ", "msci acwi"),
        ("S&P 500", "s and p 500"),
    ],
)
def test_normalisation_drops_only_decoration(raw: str, canonical: str) -> None:
    assert parse_index_name(raw).canonical == canonical


@pytest.mark.parametrize(
    "raw,variant",
    [
        ("MSCI ACWI Index (Net)", ReturnVariant.NET),
        ("MSCI ACWI (Net Total Return)", ReturnVariant.NET),
        ("MSCI ACWI (TRN)", ReturnVariant.NET),
        ("MSCI World (Gross)", ReturnVariant.GROSS),
        ("MSCI World (TR)", ReturnVariant.GROSS),
        ("MSCI World (Price)", ReturnVariant.PRICE),
        ("MSCI ACWI", None),
    ],
)
def test_return_variant_is_extracted_not_discarded(raw, variant) -> None:
    """The variant is a separate field, not noise: a gross series is a
    different series from a net one, and A5.5 requires net."""
    assert parse_index_name(raw).variant is variant


@pytest.mark.parametrize(
    "raw,hedging",
    [
        ("Bloomberg Global Aggregate Bond Index (EUR Hedged)", Hedging.EUR_HEDGED),
        ("Bloomberg Global Aggregate Bond Index (EUR-Hedged)", Hedging.EUR_HEDGED),
        ("Bloomberg Global Aggregate Bond Index (USD Hedged)", Hedging.OTHER_HEDGED),
        ("Bloomberg Global Aggregate Bond Index", None),
    ],
)
def test_hedging_tag_is_extracted(raw, hedging) -> None:
    assert parse_index_name(raw).hedging is hedging


@pytest.mark.parametrize(
    "a,b",
    [
        # Anything that changes the constituent set must survive normalisation.
        ("MSCI World Quality", "MSCI World Sector Neutral Quality"),
        ("MSCI World", "MSCI World ESG Screened"),
        ("MSCI World", "MSCI World SRI"),
        ("MSCI World", "MSCI Europe"),
        ("FTSE EMU Government Bond Index 1-3 Years", "FTSE EMU Government Bond Index"),
        ("FTSE EMU Government Bond Index 1-3 Years", "FTSE EMU Government Bond Index 10+ Years"),
        ("MSCI World", "MSCI World Leveraged 2x"),
    ],
)
def test_constituent_changing_parts_are_never_normalised_away(a: str, b: str) -> None:
    assert parse_index_name(a).canonical != parse_index_name(b).canonical


# --- matching against the registry -------------------------------------------


def _registry() -> IndexRegistry:
    reg = IndexRegistry()
    reg.register_alias(
        Alias(
            block=BuildingBlock.K2_MONEY_MARKET,
            raw="ESTR Compounded",
            source_type=SourceType.KID,
            as_of=dt.date(2026, 9, 1),
        )
    )
    return reg


def test_canonical_a5_5_name_matches_without_any_alias() -> None:
    reg = IndexRegistry()
    m = reg.match(BuildingBlock.K1, "MSCI ACWI Index (Net)")
    assert m.verdict is MatchVerdict.MATCH


def test_registered_alias_matches() -> None:
    m = _registry().match(BuildingBlock.K2_MONEY_MARKET, "ESTR Compounded")
    assert m.verdict is MatchVerdict.MATCH
    assert m.alias is not None
    assert m.alias.source_type is SourceType.KID


def test_unknown_name_is_unknown_not_mismatch() -> None:
    """A name nobody registered is a gap in the data, not proof of a wrong
    index — it must end open, with the normalised form in the reason."""
    m = IndexRegistry().match(BuildingBlock.K2_MONEY_MARKET, "Solactive €STR +8.5bp")
    assert m.verdict is MatchVerdict.UNKNOWN
    assert "solactive" in m.reason


def test_wrong_index_is_a_real_mismatch() -> None:
    """A known index of another building block is a genuine rejection."""
    m = IndexRegistry().match(BuildingBlock.K1, "FTSE EMU Government Bond Index")
    assert m.verdict is MatchVerdict.MISMATCH


def test_alias_of_one_block_does_not_leak_into_another() -> None:
    m = _registry().match(BuildingBlock.K1, "ESTR Compounded")
    assert m.verdict is not MatchVerdict.MATCH


def test_s_factor_canonical_is_the_sector_neutral_index() -> None:
    """v1.7 correction: the plain Quality index is a different index."""
    reg = IndexRegistry()
    assert reg.match(
        BuildingBlock.S_FACTOR, "MSCI World Sector Neutral Quality Index (Net)"
    ).verdict is MatchVerdict.MATCH
    assert reg.match(
        BuildingBlock.S_FACTOR, "MSCI World Quality Index (Net)"
    ).verdict is not MatchVerdict.MATCH


def test_egbi_parent_and_every_maturity_band_match() -> None:
    reg = IndexRegistry()
    for band in ("", " 1-3 Years", " 3-5 Years", " 5-7 Years", " 7-10 Years", " 10+ Years"):
        raw = f"FTSE EMU Government Bond Index{band}"
        assert reg.match(BuildingBlock.K2_EUR_GOVERNMENT_BONDS, raw).verdict is MatchVerdict.MATCH


def test_alias_requires_a_document_class_and_as_of_date() -> None:
    """An alias is data (A5.1), so it carries where it was read and when."""
    with pytest.raises(TypeError):
        Alias(block=BuildingBlock.K1, raw="whatever")  # type: ignore[call-arg]


# --- narrowing vs. derived series (v1.7, found by probing the fix) ----------


def test_narrowed_equity_index_is_a_mismatch_not_a_gap() -> None:
    """"MSCI ACWI ex USA" drops a market: a rejection, not a missing alias."""
    reg = IndexRegistry()
    m = reg.match(BuildingBlock.K1, "MSCI ACWI ex USA")
    assert m.verdict is MatchVerdict.MISMATCH
    assert "ex usa" in m.reason.lower()


def test_msci_world_quality_is_rejected_for_s_factor() -> None:
    """v1.7: the plain Quality index is not the sector-neutral one."""
    reg = IndexRegistry()
    m = reg.match(BuildingBlock.S_FACTOR, "MSCI World Quality")
    assert m.verdict is MatchVerdict.MISMATCH
    assert "705169" in m.reason


def test_derived_rate_series_stays_open_not_rejected() -> None:
    """A rate has no constituents to narrow.

    "ESTR Compounded" is the tradable form of €STR, so treating the extra
    word as narrowing would be the very false rejection this module removes.
    It stays unknown until an alias is read from a document.
    """
    reg = IndexRegistry()
    m = reg.match(BuildingBlock.K2_MONEY_MARKET, "ESTR Compounded")
    assert m.verdict is MatchVerdict.UNKNOWN


def test_registered_alias_makes_the_derived_series_match() -> None:
    reg = IndexRegistry()
    reg.register_alias(
        Alias(
            block=BuildingBlock.K2_MONEY_MARKET,
            raw="ESTR Compounded Index",
            source_type=SourceType.KID,
            as_of=dt.date(2026, 3, 31),
        )
    )
    assert reg.match(BuildingBlock.K2_MONEY_MARKET, "€STR Compounded").verdict is MatchVerdict.MATCH
