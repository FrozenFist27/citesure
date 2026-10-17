"""Deterministic quote verification.

A quote is valid iff, after normalising whitespace and typographic quote/dash
variants (1:1 character mapping, so offsets stay aligned), it is an exact
substring of the cited chunk's text. This is what guarantees that every
citation shown to the user is verbatim.
"""

from __future__ import annotations

import re

from citesure.models import Chunk

_CHAR_MAP = str.maketrans(
    {
        "‘": "'",
        "’": "'",
        "“": '"',
        "”": '"',
        "–": "-",
        "—": "-",
        "−": "-",
        " ": " ",
        "�": "'",  # pdf text extraction sometimes yields U+FFFD for apostrophes
    }
)


def norm_chars(s: str) -> str:
    """1:1 character normalisation (never changes string length)."""
    return s.translate(_CHAR_MAP)


def _quote_regex(quote: str) -> re.Pattern[str] | None:
    toks = norm_chars(quote).split()
    if not toks:
        return None
    return re.compile(r"\s+".join(re.escape(t) for t in toks))


def locate_quote(chunk: Chunk, quote: str) -> int | None:
    """Return the char offset of `quote` in chunk.text, or None if not verbatim."""
    rx = _quote_regex(quote)
    if rx is None:
        return None
    m = rx.search(norm_chars(chunk.text))
    return m.start() if m else None


def verify_quote(chunk: Chunk, quote: str, min_words: int = 3) -> bool:
    if len(quote.split()) < min_words:
        return False
    return locate_quote(chunk, quote) is not None


def quote_page(chunk: Chunk, quote: str) -> int:
    off = locate_quote(chunk, quote)
    return chunk.page_for_offset(off) if off is not None else chunk.page_start
