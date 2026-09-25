"""Reading the index name out of a KID (A5.1 no. 2, A5.5; spec v1.7).

A KID does not carry the benchmark in a labelled field. It states it in a
sentence — "aims to track the performance of the MSCI All Country World
Index (Net)" — and the wording differs per issuer and per language. That
sentence is the most authoritative statement of the index we can get: the
issuer is liable for it, which is why the document-class precedence in A5.1
puts the KID above any provider website.

This module does one thing: turn that sentence into an alias with its
provenance attached. It deliberately does **not** decide whether the index
is the right one — that is filter 2's job (index_identity). Separating the
two keeps a parsing mistake from ever looking like an eligibility verdict.

Two rules keep it honest:

1. **Name only what is claimed.** A sentence that *describes* an index
   ("provides daily values 0.085% higher than €STR") does not name the
   tracked one, so nothing is returned. A guess here would be written into
   the registry as a fact.
2. **Nothing without a date and a document class.** An alias is only worth
   storing together with the document it came from and that document's
   as-of date, because index names change (the fund above switched index in
   November 2023 and the KID still shows both).
"""

from __future__ import annotations

import datetime as dt
import re

from trading_app.hard_filters import BuildingBlock
from trading_app.index_identity import Alias
from trading_app.instruments import SourceType

__all__ = [
    "extract_index_name",
    "extract_index_names",
    "aliases_from_kid",
    "index_name_from_pdf",
]


# The most authoritative statement in a KID is the labelled benchmark line
# ("† Benchmark: MSCI All Country World Index (Net)"), because it is the
# issuer's formal designation rather than descriptive prose. It is also
# where the return variant appears, which the prose usually omits — so it is
# tried first.
_BENCHMARK_LABEL = re.compile(
    r"(?i:benchmark|vergleichsindex|referenzwert)\s*[:†]?\s*"
    r"([A-Z€][\w€&.+%-]*(?:\s+[\w€&.+%()-]+){0,9}?"
    r"(?:\s*\((?i:net|gross|price|total\s+return)[^)]{0,20}\)|\s+Index))",
)


# Verbs that introduce the tracked index, English and German. The German
# forms matter: KIDs for the same fund are filed per distribution country,
# and henri's are the German ones.
_TRACKING_VERB = r"""
    (?i:
        track(?:s|ing)?
      | reflect(?:s|ing)?
      | replicat(?:e|es|ing)
      | return\s+of
      | performance\s+of
      | nachzubilden
      | nachbildet
      | abbildet
      | Wertentwicklung\s+des
    )
"""

# An index name: starts at a capital letter or a currency symbol (€STR), runs
# through words, digits, +, ., & and hyphens, ends at "Index" or at a
# trailing variant parenthetical such as "(Net)". The parenthetical is
# restricted to actual variant words — a KID often writes "... Index
# (index)" or "(the Index)" to introduce a defined term, and that is
# punctuation, not part of the name.
_VARIANT_PAREN = r"""
    (?:\s*\((?i:net|gross|price|total\s+return|net\s+total\s+return|
              nettorendite|kursindex)[^)]{0,15}\))?
"""

_INDEX_NAME = rf"""
    (
        [A-Z€][\w€&.+-]*
        (?:\s+[\w€&.+%-]+){{0,9}}?
        \s+Index
        {_VARIANT_PAREN}
      |
        [A-Z€][\w€&.+-]*
        (?:\s+[\w€&.+%-]+){{0,9}}?
        \s*\((?i:Net|Gross|Price|Total\s+Return)[^)]{{0,20}}\)
    )
"""

_PATTERN = re.compile(
    rf"{_TRACKING_VERB}\s+(?i:the\s+|des\s+|der\s+|dem\s+)?{_INDEX_NAME}",
    re.VERBOSE,
)

# Sentences that describe an index rather than naming the tracked one. Their
# subject is already "the Index", so any name they contain is a definition,
# not a claim about what the fund follows.
_DESCRIBES_NOT_NAMES = re.compile(
    r"^\s*(?:the\s+)?index\s+(?:provides|is\s+designed|measures|represents)",
    re.IGNORECASE,
)

_LEADING_ARTICLE = re.compile(r"^(?:the|des|der|dem|das)\s+", re.IGNORECASE)


def _flatten(text: str) -> str:
    """PDF text arrives with hard line breaks mid-sentence."""
    return re.sub(r"\s+", " ", text).strip()


def extract_index_names(text: str) -> tuple[str, ...]:
    """Every distinct spelling the document uses for its index.

    A KID is not consistent with itself: iShares writes "MSCI All Countries
    World Index" in the objective and "MSCI All Country World Index (Net)"
    on the benchmark line of the same page. Both are spellings a source file
    may later contain, so both are worth registering — collecting only the
    "best" one would leave the other to be rejected as unknown.

    Ordered most authoritative first (benchmark label, then prose).
    """
    flat = _flatten(text)
    found: list[str] = []

    def _add(name: str) -> None:
        name = _LEADING_ARTICLE.sub("", name).strip(" .,;:")
        if name and name not in found:
            found.append(name)

    for match in _BENCHMARK_LABEL.finditer(flat):
        _add(match.group(1))

    for sentence in re.split(r"(?<=[.;])\s+", flat):
        if _DESCRIBES_NOT_NAMES.match(sentence):
            continue
        match = _PATTERN.search(sentence)
        if match is not None:
            _add(match.group(1))

    return tuple(found)


def extract_index_name(text: str) -> str | None:
    """The single most authoritative index name, or ``None``.

    ``None`` is a real answer and the safe one: it means "this document does
    not state it", which leaves filter 2 open for a human to resolve. It
    never means "no index".
    """
    names = extract_index_names(text)
    return names[0] if names else None


def aliases_from_kid(
    text: str,
    *,
    block: BuildingBlock,
    source_type: SourceType,
    as_of: dt.date,
) -> tuple[Alias, ...]:
    """Turn a document's own wording into registrable aliases.

    Returns a tuple because a document may legitimately name none — an empty
    result is the normal outcome for an actively managed fund and must not
    be mistaken for a failure.
    """
    name = extract_index_name(text)
    if name is None:
        return ()
    return tuple(
        Alias(block=block, raw=n, source_type=source_type, as_of=as_of)
        for n in extract_index_names(text)
    )


def index_name_from_pdf(path: str) -> str | None:
    """Same, for a downloaded KID on disk.

    Only the first three pages are read: the objective sits on page 1 of a
    PRIIPs KID, and reading further only invites a past-performance section
    that names superseded indices (see the module docstring).
    """
    from pypdf import PdfReader

    reader = PdfReader(path)
    text = " ".join(page.extract_text() or "" for page in reader.pages[:3])
    return extract_index_name(text)
