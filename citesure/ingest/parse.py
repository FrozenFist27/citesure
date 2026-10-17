"""PDF parsing with pdfplumber: text, font sizes (headings), tables, page numbers.

Produces an ordered list of Block objects per document:
- headings (font-size / bold / section-pattern aware)
- body text lines grouped into paragraphs
- tables converted to Markdown

Running headers/footers (same text at the same y-band on >50% of pages) are
dropped. Table regions are removed from body text so nothing is duplicated.
"""

from __future__ import annotations

import re
import statistics
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable

import pdfplumber

# Section-numbered heading, e.g. "3.2.1 Detection and Analysis" or "2.1. Life Cycle"
RE_SECTION = re.compile(r"^(\d+(?:\.\d+)*\.?)\s+\S")
# CSF-style category id, e.g. "PR.AA" (two letter groups separated by a dot)
RE_CSF_ID = re.compile(r"^[A-Z]{2}\.[A-Z]{2}$")
# CSF subcategory, e.g. "PR.AA-01" - an inline label, not a heading
RE_CSF_SUB = re.compile(r"^[A-Z]{2}\.[A-Z]{2}-\d+")
RE_APPENDIX = re.compile(r"^Appendix\s+[A-Z0-9]", re.IGNORECASE)

# Requirement-level keywords that appear as bold ALL-CAPS lines inside NIST
# requirement tables (SP 800-63B). They must never be treated as headings.
REQ_KEYWORDS = {
    "shall", "should", "may", "must", "will",
    "required", "recommended", "optional", "not required",
    "shall not", "should not", "will not", "must not",
    "note", "warning", "caution", "important",
}


@dataclass
class Block:
    """One parse output unit for a single page region."""

    kind: str  # "heading" | "text" | "table"
    text: str
    page: int  # 1-based PDF page index
    level: int | None = None  # heading depth, 1-based; None for text/table
    y0: float | None = None  # top coordinate on the page (for order/debug)
    n_lines: int = 1
    meta: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class _Line:
    text: str
    page: int
    y0: float
    y1: float
    x0: float
    size: float
    bold: bool
    in_table: bool = False


def _norm_ws(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def _line_key(text: str) -> str:
    """Normalised identity for header/footer detection (ignores digits like page no.)."""
    return re.sub(r"\d+", "#", _norm_ws(text)).lower()


def _group_words_into_lines(words: list[dict[str, Any]], page_no: int) -> list[_Line]:
    """Group pdfplumber words into lines by their vertical position."""
    if not words:
        return []
    # cluster by vertical centre so differently-sized words on one visual line
    # (e.g. bold SHALL/SHOULD keywords) stay on that line
    lines: dict[int, list[dict[str, Any]]] = {}
    centres: list[float] = []
    for w in sorted(words, key=lambda w: (float(w["top"]) + float(w["bottom"])) / 2):
        c = (float(w["top"]) + float(w["bottom"])) / 2
        if centres and abs(c - centres[-1]) <= 3.0:
            lines[len(centres) - 1].append(w)
            centres[-1] = (centres[-1] + c) / 2
        else:
            centres.append(c)
            lines[len(centres) - 1] = [w]

    out: list[_Line] = []
    for band in sorted(lines):
        ws = sorted(lines[band], key=lambda w: float(w["x0"]))
        text = _norm_ws(" ".join(w["text"] for w in ws))
        if not text:
            continue
        sizes = [float(w.get("size", 0) or 0) for w in ws]
        fonts = [str(w.get("fontname", "") or "") for w in ws]
        out.append(
            _Line(
                text=text,
                page=page_no,
                y0=min(float(w["top"]) for w in ws),
                y1=max(float(w["bottom"]) for w in ws),
                x0=min(float(w["x0"]) for w in ws),
                size=max(sizes) if sizes else 0.0,
                bold=any("bold" in f.lower() for f in fonts),
            )
        )
    return out


def _table_to_markdown(rows: list[list[str | None]]) -> str:
    """Convert pdfplumber table rows (list of cells) into a Markdown table."""
    if not rows:
        return ""
    width = max(len(r) for r in rows)
    norm: list[list[str]] = []
    for r in rows:
        cells = [(_norm_ws(c) if c else "") for c in list(r) + [None] * (width - len(r))]
        norm.append(cells)
        width = max(width, len(cells))
    # pad again in case ragged
    norm = [r + [""] * (width - len(r)) for r in norm]
    header = norm[0]
    body = norm[1:]
    lines = [
        "| " + " | ".join(header) + " |",
        "| " + " | ".join("---" for _ in header) + " |",
    ]
    for r in body:
        lines.append("| " + " | ".join(r) + " |")
    return "\n".join(lines)


def _detect_heading_level(line: _Line, median_size: float) -> int | None:
    """Return heading level (1-based) or None if the line is not a heading."""
    text = line.text
    if RE_CSF_SUB.match(text):
        return None  # inline subcategory label

    is_short = len(text) <= 90
    is_all_caps = is_short and text.isupper() and len(text.split()) <= 12 and any(c.isalpha() for c in text)
    # reject requirement-keyword lines: "SHALL", "SHOULD NOT", ...
    words_norm = [w.strip(".,:;()-–—").lower() for w in text.split() if w.strip(".,:;()-–—")]
    if words_norm and all(w in REQ_KEYWORDS for w in words_norm):
        return None
    matches_section = bool(RE_SECTION.match(text))
    csf_id_only = bool(RE_CSF_ID.match(text.rstrip(":")))
    appendix = bool(RE_APPENDIX.match(text)) and is_short

    bigger = line.size >= median_size + 1.5
    strong = line.bold or is_all_caps

    if not (matches_section or csf_id_only or appendix or is_all_caps):
        return None
    if not (bigger or strong or csf_id_only):
        return None
    # Guard: long bold paragraphs are not headings
    if len(text.split()) > 16:
        return None

    m = RE_SECTION.match(text)
    if m:
        # level = depth of the section number, ignoring a trailing dot ("2.1." -> 2)
        num = m.group(1).rstrip(".")
        return num.count(".") + 1
    if csf_id_only:
        return 1
    if appendix or is_all_caps:
        return 1
    return 1


RE_PAGE_FOLIO = re.compile(r"^(?:page\s+)?[\divxlIVXL]+(?:\s*[-–]\s*[\divxlIVXL]+)?$", re.IGNORECASE)


def _drop_running_headers_footers(
    all_lines: list[_Line], n_pages: int, page_heights: dict[int, float]
) -> set[int]:
    """Index lines that are running headers/footers.

    Two rules:
    1. Bare folios ("4", "Page 4", "iv") in the top/bottom 10% of any page.
    2. Text (normalised, ignoring digits) repeated at the same y-band on >50% of pages.
    """
    drop: set[int] = set()
    key_pages: dict[str, set[int]] = {}

    for i, ln in enumerate(all_lines):
        height = page_heights.get(ln.page) or 792.0
        in_strip = ln.y0 < height * 0.10 or ln.y1 > height * 0.90
        if in_strip and RE_PAGE_FOLIO.match(ln.text.strip()):
            drop.add(i)
            continue
        if len(ln.text) < 4:
            continue
        band = int(ln.y0 // 15)
        key_pages.setdefault((_line_key(ln.text), band), set()).add(ln.page)

    if n_pages <= 1:
        return drop

    drop_keys = {k for k, pages in key_pages.items() if len(pages) > n_pages * 0.5}
    for i, ln in enumerate(all_lines):
        band = int(ln.y0 // 15)
        if (_line_key(ln.text), band) in drop_keys:
            drop.add(i)
    return drop


def _merge_paragraphs(lines: Iterable[_Line]) -> list[str]:
    """Merge consecutive body lines into paragraph strings (start new on gaps)."""
    paras: list[str] = []
    cur: list[str] = []
    prev: _Line | None = None
    for ln in lines:
        if prev is not None and (ln.y0 - prev.y1 > 6 or ln.page != prev.page):
            if cur:
                paras.append(_norm_ws(" ".join(cur)))
            cur = []
        cur.append(ln.text)
        prev = ln
    if cur:
        paras.append(_norm_ws(" ".join(cur)))
    return [p for p in paras if p]


def parse_pdf(path: str | Path, doc_id: str | None = None) -> list[Block]:
    """Parse a born-digital PDF into ordered Blocks (headings, text, tables)."""
    path = Path(path)
    blocks: list[Block] = []

    with pdfplumber.open(path) as pdf:
        n_pages = len(pdf.pages)
        page_lines: list[list[_Line]] = []
        page_tables: list[list[tuple[str, tuple[float, float, float, float]]]] = []
        page_heights: dict[int, float] = {}

        for page_no, page in enumerate(pdf.pages, start=1):
            page_heights[page_no] = float(page.height or 792.0)
            words = page.extract_words(extra_attrs=["size", "fontname"], keep_blank_chars=False)
            lines = _group_words_into_lines(words, page_no)

            tables_md: list[tuple[str, tuple[float, float, float, float]]] = []
            for t in page.find_tables():
                try:
                    data = t.extract()
                except Exception:  # noqa: BLE001 - malformed table, skip it
                    continue
                if not data or all(all(not (c or "").strip() for c in row) for row in data):
                    continue
                md = _table_to_markdown(data)
                if md:
                    tables_md.append((md, tuple(t.bbox)))  # type: ignore[arg-type]

            # mark lines that sit inside a table bbox
            for ln in lines:
                cy = (ln.y0 + ln.y1) / 2
                for _md, (tx0, ty0, tx1, ty1) in tables_md:
                    if ty0 - 1 <= cy <= ty1 + 1:
                        ln.in_table = True
                        break

            page_lines.append(lines)
            page_tables.append(tables_md)

    # document-level median font size (body text estimate)
    sizes = [ln.size for lines in page_lines for ln in lines if not ln.in_table and ln.size > 0]
    median_size = statistics.median(sizes) if sizes else 10.0

    # header/footer detection across the whole document
    flat = [ln for lines in page_lines for ln in lines]
    drop_idx = _drop_running_headers_footers(flat, n_pages, page_heights)

    for page_no, (lines, tables) in enumerate(zip(page_lines, page_tables), start=1):
        # headings and paragraphs in y-order, skipping table regions and running heads
        body_lines: list[_Line] = []
        pending: list[_Line] = []
        for i, ln in enumerate(lines):
            global_idx = sum(len(pl) for pl in page_lines[: page_no - 1]) + i
            if global_idx in drop_idx or ln.in_table:
                if pending:
                    for p in _merge_paragraphs(pending):
                        blocks.append(Block(kind="text", text=p, page=page_no))
                    pending = []
                continue
            level = _detect_heading_level(ln, median_size)
            if level is not None:
                if pending:
                    for p in _merge_paragraphs(pending):
                        blocks.append(Block(kind="text", text=p, page=page_no))
                    pending = []
                blocks.append(
                    Block(kind="heading", text=ln.text, page=page_no, level=level, y0=ln.y0)
                )
            else:
                body_lines.append(ln)
                pending.append(ln)
        if pending:
            for p in _merge_paragraphs(pending):
                blocks.append(Block(kind="text", text=p, page=page_no))

        # tables as their own blocks (after the text that precedes them on the page)
        for md, bbox in tables:
            blocks.append(
                Block(
                    kind="table",
                    text=md,
                    page=page_no,
                    y0=bbox[1],
                    meta={"bbox": list(bbox)},
                )
            )

    return blocks


def parse_summary(blocks: list[Block]) -> dict[str, Any]:
    return {
        "n_blocks": len(blocks),
        "n_headings": sum(1 for b in blocks if b.kind == "heading"),
        "n_text": sum(1 for b in blocks if b.kind == "text"),
        "n_tables": sum(1 for b in blocks if b.kind == "table"),
        "n_words": sum(len(b.text.split()) for b in blocks if b.kind != "table"),
    }
