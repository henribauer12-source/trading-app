"""Reading the index name out of a KID (A5.1, A5.5; spec v1.7).

A KID names its index in prose, not in a field: "aims to track the
performance of the MSCI All Country World Index (Net)". These tests pin the
extraction against text taken from real documents, so the parser can be
exercised without the network — the download itself is covered by
sources/documents.py and is not repeated here.
"""

from __future__ import annotations

import datetime as dt

import pytest

from trading_app.hard_filters import BuildingBlock
from trading_app.instruments import SourceType
from trading_app.sources.kid_index import (
    extract_index_name,
    aliases_from_kid,
)

# Sentences as they appear in the documents (whitespace flattened, as pypdf
# returns it). Each is a shape the extractor must survive.
_REAL_KID_SENTENCES = [
    (
        "The Fund aims to achieve a return on your investment which reflects "
        "the return of the MSCI All Country World Index (Net), the Fund's "
        "benchmark index.",
        "MSCI All Country World Index (Net)",
    ),
    (
        "The fund's investment objective is to reflect the performance of the "
        "Solactive €STR +8.5 Daily Total Return Index (index).",
        "Solactive €STR +8.5 Daily Total Return Index",
    ),
    (
        "The Index provides daily values representing a value 0.085% higher "
        "than the Euro Short-Term Rate (€STR).",
        None,  # describes the index, does not name the tracked one
    ),
    (
        "Der Fonds strebt an, die Wertentwicklung des FTSE All-World Index "
        "nachzubilden.",
        "FTSE All-World Index",
    ),
]


@pytest.mark.parametrize(("text", "expected"), _REAL_KID_SENTENCES)
def test_extract_index_name_from_real_sentences(text: str, expected: str | None) -> None:
    assert extract_index_name(text) == expected


def test_extraction_stops_at_the_sentence_end() -> None:
    """The name must not swallow the rest of the paragraph."""
    text = (
        "The Fund aims to track the MSCI World Sector Neutral Quality Index "
        "(Net). The Fund is passively managed."
    )
    assert extract_index_name(text) == "MSCI World Sector Neutral Quality Index (Net)"


def test_no_index_sentence_yields_none_rather_than_a_guess() -> None:
    text = "The Fund is actively managed and does not track a benchmark."
    assert extract_index_name(text) is None


def test_aliases_from_kid_carries_provenance() -> None:
    """An alias is only worth storing with its document and its date."""
    text = "The Fund aims to track the MSCI All Country World Index (Net)."
    aliases = aliases_from_kid(
        text,
        block=BuildingBlock.K1,
        source_type=SourceType.KID,
        as_of=dt.date(2026, 9, 3),
    )
    assert len(aliases) == 1
    assert aliases[0].raw == "MSCI All Country World Index (Net)"
    assert aliases[0].as_of == dt.date(2026, 9, 3)
    assert aliases[0].source_type is SourceType.KID


def test_aliases_from_kid_is_empty_when_nothing_is_named() -> None:
    aliases = aliases_from_kid(
        "The Fund is actively managed.",
        block=BuildingBlock.K1,
        source_type=SourceType.KID,
        as_of=dt.date(2026, 9, 3),
    )
    assert aliases == ()


def test_extracted_alias_makes_the_real_kid_spelling_match() -> None:
    """The point of the whole exercise, end to end.

    'MSCI All Country World Index (Net)' is what the iShares KID says; the
    spec says 'MSCI ACWI'. Registering the extracted alias must make filter 2
    accept the document's own wording.
    """
    from trading_app.index_identity import IndexRegistry, MatchVerdict

    text = "The Fund aims to track the MSCI All Country World Index (Net)."
    reg = IndexRegistry()
    assert reg.match(BuildingBlock.K1, "MSCI All Country World").verdict is MatchVerdict.UNKNOWN

    for alias in aliases_from_kid(
        text, block=BuildingBlock.K1, source_type=SourceType.KID, as_of=dt.date(2026, 9, 3)
    ):
        reg.register_alias(alias)

    assert reg.match(BuildingBlock.K1, "MSCI All Country World").verdict is MatchVerdict.MATCH
