"""Index identity for hard filter 2 (investment spec A5.2 no. 2, A5.5, v1.7).

Filter 2 asks one question: *is this the index the building block requires?*
Up to v1.6 it was answered by comparing the document's spelling with the
spelling in A5.5, character for character. That is wrong in the expensive
direction. The documents write ``MSCI ACWI Index (Net)`` where A5.5 writes
``MSCI ACWI``, and ``ESTR Compounded`` where A5.5 writes ``€STR``; both came
out as *violated*, i.e. a correct fund was rejected for a suffix. For a
filter that decides what may be bought, a false rejection is worse than an
open check: the open check asks a human, the rejection quietly removes the
product from the candidate list.

The fix is not "compare more loosely". Loose comparison fails in the other,
worse direction: ``MSCI World`` and ``MSCI World ESG Screened`` are then the
same index, and the portfolio silently holds something else than specified.
So the name is split into two parts:

- **decoration** — case, the trailing word ``Index``, the return-variant
  suffix, a currency or hedging parenthesis. Providers vary these freely for
  the same series, so they are normalised away. The variant and the hedging
  tag are *not thrown away* but extracted into their own fields, because a
  gross series is a different series from a net one (A5.5 requires net) and
  the hedging tag feeds filter 6.
- **identity** — everything that changes the constituent set:
  ``Sector Neutral``, ``ESG``, ``Screened``, ``SRI``, ``Leveraged``,
  ``Short``, a maturity band, a region. These are never normalised away, so
  a differently-composed index still fails.

What is left is matched against the canonical name of the building block or
an **alias**. An alias is data, not code: it carries the document class and
as-of date it was read from (A5.1), so the table is filled from real KIDs
and factsheets instead of from guesses. Hence three outcomes, not two: an
unregistered name is ``UNKNOWN`` (→ the filter stays *open*, and the reason
names the normalised form so the missing alias is visible), and only a name
belonging to a *different* building block is a ``MISMATCH``.
"""

from __future__ import annotations

import datetime as dt
import json
import re
import unicodedata
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path

from trading_app.hard_filters import BuildingBlock
from trading_app.instruments import SourceType


class ReturnVariant(StrEnum):
    """How the index treats dividends. A5.5 requires net for equities."""

    NET = "net"  # dividends after withholding tax
    GROSS = "gross"  # dividends reinvested in full
    PRICE = "price"  # no dividends at all


class Hedging(StrEnum):
    EUR_HEDGED = "eur_hedged"
    OTHER_HEDGED = "other_hedged"  # hedged, but not into EUR → filter 6


class MatchVerdict(StrEnum):
    MATCH = "match"
    MISMATCH = "mismatch"  # a known index, but of another building block
    UNKNOWN = "unknown"  # nobody registered this name → data gap, not proof


# Suffixes naming the return variant. Longest first, so "(net total return)"
# is not eaten by "(net)". ``TR`` means gross in MSCI's notation, ``TRN`` net.
_VARIANTS: tuple[tuple[str, ReturnVariant], ...] = (
    ("net total return", ReturnVariant.NET),
    ("gross total return", ReturnVariant.GROSS),
    ("total return net", ReturnVariant.NET),
    ("total return gross", ReturnVariant.GROSS),
    ("price return", ReturnVariant.PRICE),
    ("trn", ReturnVariant.NET),
    ("ntr", ReturnVariant.NET),
    ("net", ReturnVariant.NET),
    ("gross", ReturnVariant.GROSS),
    ("gr", ReturnVariant.GROSS),
    ("tr", ReturnVariant.GROSS),
    ("price", ReturnVariant.PRICE),
)

_HEDGING = re.compile(r"\b(?P<ccy>[a-z]{3})[\s-]*hedged\b")


@dataclass(frozen=True, slots=True)
class ParsedIndex:
    """A document's index name, split into identity and decoration."""

    raw: str
    canonical: str
    variant: ReturnVariant | None
    hedging: Hedging | None


def _strip_diacritics(text: str) -> str:
    # € is not decomposable, so it is mapped explicitly: the ECB writes €STR,
    # the providers write ESTR, and both mean the same rate.
    text = text.replace("€", "e")
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(c for c in decomposed if not unicodedata.combining(c))


def parse_index_name(raw: str) -> ParsedIndex:
    """Split a document's index name into identity, return variant, hedging."""
    text = _strip_diacritics(raw).lower()
    text = text.replace("&", " and ")
    # Dashes vary (en dash, em dash, hyphen) — fold them, but keep them, as
    # a maturity band "1-3" is identity.
    text = re.sub(r"[\u2010-\u2015]", "-", text)

    hedging: Hedging | None = None
    variant: ReturnVariant | None = None

    def _take_parenthetical(match: re.Match[str]) -> str:
        nonlocal hedging, variant
        inner = match.group(1).strip()
        if (hedge := _HEDGING.fullmatch(inner)) is not None:
            hedging = (
                Hedging.EUR_HEDGED if hedge.group("ccy") == "eur" else Hedging.OTHER_HEDGED
            )
            return " "
        for token, found in _VARIANTS:
            if inner == token:
                variant = found
                return " "
        return match.group(0)  # not decoration → identity, keep it

    text = re.sub(r"\(([^()]*)\)", _take_parenthetical, text)

    # The same tags also appear without brackets, at the end of the name.
    if hedging is None and (hedge := _HEDGING.search(text)) is not None:
        # Only when trailing: "... eur hedged". A leading "hedged" would be
        # part of the name and is left alone.
        if hedge.end() == len(text.rstrip()):
            hedging = (
                Hedging.EUR_HEDGED if hedge.group("ccy") == "eur" else Hedging.OTHER_HEDGED
            )
            text = text[: hedge.start()]

    # A trailing "index" carries no identity: every index is an index.
    text = re.sub(r"\bindex\b\s*$", " ", text.strip())
    # ... and it also sits in the middle, before the variant we just removed.
    text = re.sub(r"\bindex\b\s*$", " ", text.strip())
    canonical = re.sub(r"\s+", " ", text).strip(" -,")
    return ParsedIndex(raw=raw, canonical=canonical, variant=variant, hedging=hedging)


@dataclass(frozen=True, slots=True)
class Alias:
    """A spelling read from a real document (A5.1: class and as-of date)."""

    block: BuildingBlock
    raw: str
    source_type: SourceType
    as_of: object  # datetime.date; kept loose to avoid an import cycle

    @property
    def canonical(self) -> str:
        return parse_index_name(self.raw).canonical


@dataclass(frozen=True, slots=True)
class Match:
    verdict: MatchVerdict
    parsed: ParsedIndex
    block: BuildingBlock
    reason: str
    alias: Alias | None = None


# The canonical names of A5.5, in the spelling of the specification. They are
# run through the same normalisation as the documents, so the table may be
# written the way A5.5 writes it.
_CANONICAL_A5_5: dict[BuildingBlock, tuple[str, ...]] = {
    BuildingBlock.K1: ("MSCI ACWI", "MSCI ACWI IMI", "FTSE All-World"),
    # €STR itself is not investable (v1.7): funds track a derived series,
    # which has to arrive as an alias from a real document.
    BuildingBlock.K2_MONEY_MARKET: ("€STR",),
    BuildingBlock.K2_EUR_GOVERNMENT_BONDS: (
        "FTSE EMU Government Bond Index",
        "FTSE EMU Government Bond Index 1-3 Years",
        "FTSE EMU Government Bond Index 3-5 Years",
        "FTSE EMU Government Bond Index 5-7 Years",
        "FTSE EMU Government Bond Index 7-10 Years",
        "FTSE EMU Government Bond Index 10+ Years",
    ),
    BuildingBlock.K2_GLOBAL_BONDS: ("Bloomberg Global Aggregate Bond Index",),
    # S-Gold has no index: filter 2 checks the reference price instead.
    BuildingBlock.S_GOLD: ("LBMA Gold Price PM",),
    # v1.7 correction: the products track the sector-neutral variant
    # (MSCI 705169), not the plain Quality index (MSCI 702787).
    BuildingBlock.S_FACTOR: ("MSCI World Sector Neutral Quality",),
}

# Building blocks whose canonical entry is a **rate or a reference price**,
# not an investable index. Extra words there do not narrow a constituent set
# — they name the tradable series derived from the rate ("€STR Compounded",
# "€STR + 8.5bp"). Applying the narrowing rule to these would recreate
# exactly the false rejection this module exists to remove, so an unfamiliar
# derived name stays UNKNOWN (→ open) until an alias is read from a document.
_RATE_BLOCKS = frozenset({BuildingBlock.K2_MONEY_MARKET, BuildingBlock.S_GOLD})


# Names the specification itself names, which are eligible for **no** building
# block. Without this they would be "unknown" and the filter would merely ask
# a human about an index the spec has already ruled out. Keeping them here is
# what separates "we have not read this yet" from "this is the wrong index".
_KNOWN_NOT_ELIGIBLE: dict[str, str] = {
    # A5.4: World + EM at market weight is a combination at the user's
    # request, not a single fund for K1, and A5.2 on 2 does not model it.
    "msci world": "the A5.4 alternative MSCI World + MSCI EM, which is not modelled",
    "msci emerging markets": (
        "the A5.4 alternative MSCI World + MSCI EM, which is not modelled"
    ),
    "msci em": "the A5.4 alternative MSCI World + MSCI EM, which is not modelled",
    # v1.7: the plain Quality index (MSCI 702787) is *not* the one the
    # products track; A5.5 now requires the sector-neutral variant (705169).
    "msci world quality": (
        "MSCI World Quality (702787), which v1.7 replaced with the "
        "sector-neutral variant (705169)"
    ),
}


def load_alias_file(path: str | Path) -> tuple[Alias, ...]:
    """Read aliases pulled from documents (``data/index_aliases.json``).

    Every entry must carry its document class and date; an entry without
    them is rejected rather than defaulted, because provenance is what
    separates a registered alias from a guess.
    """
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    out: list[Alias] = []
    for i, entry in enumerate(raw.get("aliases", [])):
        missing = [k for k in ("block", "raw", "source_type", "as_of") if not entry.get(k)]
        if missing:
            raise ValueError(f"alias #{i} in {path} is missing {', '.join(missing)}")
        out.append(
            Alias(
                block=BuildingBlock[entry["block"]],
                raw=entry["raw"],
                source_type=SourceType[entry["source_type"]],
                as_of=dt.date.fromisoformat(entry["as_of"]),
            )
        )
    return tuple(out)


def default_registry(path: str | Path | None = None) -> IndexRegistry:
    """A registry loaded with the aliases pulled so far."""
    if path is None:
        path = Path(__file__).resolve().parents[2] / "data" / "index_aliases.json"
    reg = IndexRegistry()
    if Path(path).exists():
        for alias in load_alias_file(path):
            reg.register_alias(alias)
    return reg


class IndexRegistry:
    """Canonical A5.5 names plus aliases read from documents."""

    def __init__(self) -> None:
        self._canonical: dict[BuildingBlock, set[str]] = {
            block: {parse_index_name(name).canonical for name in names}
            for block, names in _CANONICAL_A5_5.items()
        }
        self._aliases: dict[BuildingBlock, list[Alias]] = {}

    def register_alias(self, alias: Alias) -> None:
        self._aliases.setdefault(alias.block, []).append(alias)

    def aliases(self, block: BuildingBlock) -> tuple[Alias, ...]:
        return tuple(self._aliases.get(block, ()))

    def match(self, block: BuildingBlock, raw: str) -> Match:
        parsed = parse_index_name(raw)
        name = parsed.canonical

        if name in self._canonical.get(block, set()):
            return Match(
                MatchVerdict.MATCH,
                parsed,
                block,
                f"index_name = {raw!r} matches the A5.5 name for {block}",
            )

        for alias in self._aliases.get(block, []):
            if alias.canonical == name:
                return Match(
                    MatchVerdict.MATCH,
                    parsed,
                    block,
                    (
                        f"index_name = {raw!r} matches the alias {alias.raw!r} "
                        f"for {block} ({alias.source_type}, as of {alias.as_of})"
                    ),
                    alias,
                )

        # Known somewhere else → a genuine rejection, not a data gap.
        for other, names in self._canonical.items():
            if other is block:
                continue
            if name in names or any(a.canonical == name for a in self._aliases.get(other, [])):
                return Match(
                    MatchVerdict.MISMATCH,
                    parsed,
                    block,
                    (
                        f"index_name = {raw!r} is the index of {other}, "
                        f"not of {block}"
                    ),
                )

        if (ruled_out := _KNOWN_NOT_ELIGIBLE.get(name)) is not None:
            return Match(
                MatchVerdict.MISMATCH,
                parsed,
                block,
                f"index_name = {raw!r} is {ruled_out}",
            )

        # The required family with its constituents changed — e.g. "MSCI ACWI
        # ex USA" against canonical "MSCI ACWI". The extra tokens survived
        # normalisation precisely because they change what the index holds,
        # so this is a rejection and not a gap in the alias table.
        for canonical in sorted(self._canonical.get(block, set()), key=len, reverse=True):
            if block not in _RATE_BLOCKS and name.startswith(f"{canonical} "):
                extra = name[len(canonical) :].strip()
                return Match(
                    MatchVerdict.MISMATCH,
                    parsed,
                    block,
                    (
                        f"index_name = {raw!r} is {canonical!r} narrowed by "
                        f"{extra!r}, so it holds something else than {block} "
                        f"requires"
                    ),
                )

        return Match(
            MatchVerdict.UNKNOWN,
            parsed,
            block,
            (
                f"index_name = {raw!r} (normalised: {name!r}) is not a known "
                f"name or alias for {block}; register it from the KID or "
                f"factsheet before the filter can pass"
            ),
        )
