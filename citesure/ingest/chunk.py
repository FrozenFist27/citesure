"""Section-aware chunking.

Walks parsed Blocks in order, maintaining a heading stack (h1 > h2 > h3...).
A chunk is the text under the deepest heading; text longer than `max_words`
is split on sentence boundaries with ~`overlap_words` of overlap. Tables are
their own chunk with the section path as caption. Every chunk carries
page_start / page_end / section_path and a char-offset -> page map so a quote
can be resolved to a PDF page later.

Modes:
- section (default): heading-stack chunking as above
- fixed: naive ~300-word windows with overlap, no section awareness
  (used only for the before/after improvement comparison)
"""

from __future__ import annotations

import re
from typing import Any, Iterable

from citesure.ingest.parse import Block
from citesure.models import Chunk

RE_SENTENCE = re.compile(r"(?<=[.!?])\s+")


def _words(s: str) -> list[str]:
    return s.split()


def _split_with_overlap(text: str, max_words: int, overlap_words: int) -> list[str]:
    """Split text into pieces of <= max_words words, overlapping on sentence
    boundaries where possible."""
    words = _words(text)
    if len(words) <= max_words:
        return [text] if text.strip() else []

    # split into sentences first, then pack them
    sentences = RE_SENTENCE.split(text)
    pieces: list[str] = []
    cur: list[str] = []
    cur_len = 0
    for sent in sentences:
        sw = len(sent.split())
        if cur and cur_len + sw > max_words:
            pieces.append(" ".join(cur))
            # overlap: keep the tail of the current piece
            tail = _words(" ".join(cur))[-overlap_words:]
            cur = tail + sent.split()
            cur_len = len(cur)
        else:
            cur.extend(sent.split())
            cur_len += sw
    if cur:
        piece = " ".join(cur)
        # avoid a tiny trailing fragment
        if len(_words(piece)) >= 10 or not pieces:
            pieces.append(piece)

    # hard guarantee max size even with pathological sentences
    final: list[str] = []
    for p in pieces:
        pw = _words(p)
        if len(pw) <= max_words:
            final.append(p)
            continue
        for i in range(0, len(pw), max_words - overlap_words):
            window = pw[i : i + max_words]
            if len(window) >= 10 or not final:
                final.append(" ".join(window))
    return [p for p in final if p.strip()]


class _PageTracker:
    """Assemble text while recording char_offset -> page for quote resolution."""

    def __init__(self) -> None:
        self.parts: list[str] = []
        self.offsets: list[list[int]] = []
        self._len = 0
        self.pages: list[int] = []

    def add(self, text: str, page: int) -> None:
        if not text:
            return
        if self.parts:
            self.parts.append("\n\n")
            self._len += 2
        self.offsets.append([self._len, page])
        self.parts.append(text)
        self._len += len(text)
        self.pages.append(page)

    @property
    def text(self) -> str:
        return "".join(self.parts)


def _make_chunk(
    doc_id: str,
    doc_title: str,
    section_path: str,
    tracker: _PageTracker,
    seq: int,
    kind: str,
    max_words: int,
    overlap_words: int,
) -> list[Chunk]:
    text = tracker.text
    if not text.strip():
        return []
    pages = tracker.pages or [1]
    page_start, page_end = min(pages), max(pages)
    chunk_id = f"{doc_id}:{page_start}:{seq:03d}"
    context = f"{doc_title} > {section_path}\n{text}" if section_path else f"{doc_title}\n{text}"

    pieces = (
        [(text, tracker.offsets)]
        if kind == "table" or len(_words(text)) <= max_words
        else _split_offset_text(text, tracker.offsets, max_words, overlap_words)
    )

    out: list[Chunk] = []
    for i, (piece, offsets) in enumerate(pieces):
        pgs = [o[1] for o in offsets] or pages
        cid = chunk_id if i == 0 else f"{doc_id}:{min(pgs)}:{seq:03d}.{i}"
        ctxt = f"{doc_title} > {section_path}\n{piece}" if section_path else f"{doc_title}\n{piece}"
        out.append(
            Chunk(
                chunk_id=cid,
                doc_id=doc_id,
                doc_title=doc_title,
                section_path=section_path,
                page_start=min(pgs),
                page_end=max(pgs),
                kind=kind,  # type: ignore[arg-type]
                text=piece,
                context_text=ctxt,
                n_words=len(_words(piece)),
                page_offsets=offsets,
            )
        )
    return out


def _split_offset_text(
    text: str, offsets: list[list[int]], max_words: int, overlap_words: int
) -> list[tuple[str, list[list[int]]]]:
    """Split text on sentence boundaries keeping the char->page offsets."""
    pieces = _split_with_overlap(text, max_words, overlap_words)
    if len(pieces) == 1:
        return [(text, offsets)]

    out: list[tuple[str, list[list[int]]]] = []
    cursor = 0  # search position in text
    for piece in pieces:
        idx = text.find(piece, cursor)
        if idx < 0:  # overlap text may not be contiguous; fall back to first offsets
            idx = cursor
        end = idx + len(piece)
        sub = [
            [max(0, o[0] - idx), o[1]]
            for o in offsets
            if o[0] + 0 <= end  # keep offsets up to the end of this piece
        ]
        # drop offsets that start after this piece
        sub = [o for o in sub if o[0] < len(piece) or o[0] == 0]
        sub = sorted({tuple(o) for o in sub})
        norm = [[int(a), int(b)] for a, b in sub] or [[0, offsets[0][1]]]
        out.append((piece, norm))
        cursor = max(cursor, idx + 1)
    return out


def chunk_document(
    blocks: Iterable[Block],
    doc_id: str,
    doc_title: str,
    mode: str = "section",
    max_words: int = 350,
    overlap_words: int = 50,
) -> list[Chunk]:
    """Turn parsed blocks into chunks. `mode` is 'section' or 'fixed'."""
    blocks = list(blocks)
    if mode == "fixed":
        return _chunk_fixed(blocks, doc_id, doc_title, max_words=300, overlap_words=50)

    chunks: list[Chunk] = []
    stack: list[tuple[int, str]] = []  # (level, heading text)
    tracker = _PageTracker()
    seq = 0

    def flush() -> None:
        nonlocal tracker, seq
        if not tracker.text.strip():
            tracker = _PageTracker()
            return
        seq += 1
        path = " > ".join(h for _, h in stack) if stack else doc_title
        chunks.extend(
            _make_chunk(
                doc_id, doc_title, path, tracker, seq, "text", max_words, overlap_words
            )
        )
        tracker = _PageTracker()

    for b in blocks:
        if b.kind == "heading" and b.level is not None:
            flush()
            while stack and stack[-1][0] >= b.level:
                stack.pop()
            stack.append((b.level, b.text))
        elif b.kind == "table":
            flush()
            seq += 1
            path = " > ".join(h for _, h in stack) if stack else doc_title
            t_tracker = _PageTracker()
            caption = path.split(" > ")[-1] if stack else doc_title
            t_tracker.add(f"{caption}\n\n{b.text}", b.page)
            chunks.extend(
                _make_chunk(doc_id, doc_title, path, t_tracker, seq, "table", max_words, overlap_words)
            )
        else:  # text
            tracker.add(b.text, b.page)
    flush()
    return chunks


def _chunk_fixed(
    blocks: list[Block], doc_id: str, doc_title: str, max_words: int, overlap_words: int
) -> list[Chunk]:
    """Fixed-size window chunking, ignoring section structure (baseline only)."""
    chunks: list[Chunk] = []
    tracker = _PageTracker()
    seq = 0
    for b in blocks:
        if b.kind == "heading":
            continue
        tracker.add(b.text, b.page)
        while len(_words(tracker.text)) >= max_words:
            seq += 1
            piece_tracker = _PageTracker()
            words = _words(tracker.text)
            piece_words = words[:max_words]
            piece_text = " ".join(piece_words)
            # keep offsets whose start is inside this piece's char length
            piece_tracker.add(piece_text, tracker.pages[0])
            piece_tracker.offsets = [[0, tracker.pages[0]]]
            # approximate page map: assign pages by proportion
            piece_tracker.offsets = []
            approx_len = len(piece_text)
            step = max(1, approx_len // max(1, len(tracker.pages)))
            for i, pg in enumerate(tracker.pages):
                off = min(i * step, approx_len)
                piece_tracker.offsets.append([off, pg])
            chunks.extend(
                _make_chunk(
                    doc_id,
                    doc_title,
                    "(fixed)",
                    piece_tracker,
                    seq,
                    "text",
                    max_words,
                    overlap_words,
                )
            )
            # slide the window by (max_words - overlap_words)
            keep = words[max_words - overlap_words :]
            new_tracker = _PageTracker()
            new_tracker.add(" ".join(keep), tracker.pages[-1] if tracker.pages else 1)
            new_tracker.offsets = [[0, tracker.pages[0] if tracker.pages else 1]]
            new_tracker.pages = tracker.pages
            tracker = new_tracker
            if len(_words(tracker.text)) < max_words:
                break
    if tracker.text.strip():
        seq += 1
        chunks.extend(
            _make_chunk(doc_id, doc_title, "(fixed)", tracker, seq, "text", max_words, overlap_words)
        )
    return chunks


def chunk_stats(chunks: list[Chunk]) -> dict[str, Any]:
    words = [c.n_words for c in chunks]
    return {
        "n_chunks": len(chunks),
        "mean_words": round(sum(words) / max(len(words), 1), 1),
        "max_words": max(words) if words else 0,
        "n_tables": sum(1 for c in chunks if c.kind == "table"),
        "n_docs": len({c.doc_id for c in chunks}),
    }
