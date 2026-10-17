"""Ingest CLI: parse / chunk / index the corpus.

  python -m citesure.ingest.cli parse --doc sp800-61r3 [--page 1]
  python -m citesure.ingest.cli chunk --doc sp800-61r3
  python -m citesure.ingest.cli all
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import yaml

from citesure.config import load_settings


def _manifest_docs() -> dict[str, dict]:
    s = load_settings()
    manifest = yaml.safe_load(s.manifest_path.read_text(encoding="utf-8"))
    return {d["doc_id"]: d for d in manifest["documents"]}


def _pdf_path(entry: dict) -> Path:
    return load_settings().docs_dir / entry["filename"]


def cmd_parse(args: argparse.Namespace) -> int:
    from citesure.ingest.parse import parse_pdf, parse_summary

    docs = _manifest_docs()
    if args.doc not in docs:
        print(f"unknown doc_id {args.doc!r}; have: {', '.join(docs)}")
        return 1
    entry = docs[args.doc]
    blocks = parse_pdf(_pdf_path(entry), doc_id=args.doc)
    summary = parse_summary(blocks)
    print(f"{args.doc}: {summary}")

    page = args.page
    shown = 0
    for b in blocks:
        if page and b.page != page:
            continue
        preview = b.text[:160].replace("\n", " / ")
        print(f"  [p{b.page} {b.kind}{' L' + str(b.level) if b.level else ''}] {preview}")
        shown += 1
        if args.limit and shown >= args.limit:
            break
    return 0


def cmd_chunk(args: argparse.Namespace) -> int:
    from citesure.ingest.chunk import chunk_document
    from citesure.ingest.parse import parse_pdf

    docs = _manifest_docs()
    entry = docs[args.doc]
    blocks = parse_pdf(_pdf_path(entry), doc_id=args.doc)
    chunks = chunk_document(blocks, doc_id=args.doc, doc_title=entry["title"], mode=load_settings().chunking.get("mode", "section"))
    words = [c.n_words for c in chunks]
    n_tables = sum(1 for c in chunks if c.kind == "table")
    print(
        f"{args.doc}: chunks={len(chunks)} mean_words={sum(words)/max(len(words),1):.0f} "
        f"tables={n_tables} max_words={max(words) if words else 0}"
    )
    for c in chunks[: args.limit]:
        print(f"  [{c.chunk_id}] p{c.page_start}-{c.page_end} {c.section_path!r} {c.n_words}w")
    return 0


def cmd_all(_args: argparse.Namespace) -> int:
    from citesure.ingest.chunk import chunk_document
    from citesure.ingest.index import build_index
    from citesure.ingest.parse import parse_pdf, parse_summary

    settings = load_settings()
    docs = _manifest_docs()
    t0 = time.time()
    all_chunks = []
    for doc_id, entry in docs.items():
        path = _pdf_path(entry)
        if not path.exists():
            print(f"MISSING PDF: {path} - run scripts/download_corpus.py first")
            return 1
        blocks = parse_pdf(path, doc_id=doc_id)
        print(f"parse  {doc_id}: {parse_summary(blocks)}")
        chunks = chunk_document(
            blocks,
            doc_id=doc_id,
            doc_title=entry["short_title"],
            mode=settings.chunking.get("mode", "section"),
        )
        all_chunks.extend(chunks)
    t_parse = time.time() - t0

    words = [c.n_words for c in all_chunks]
    print(
        f"chunk totals: {len(all_chunks)} chunks, mean_words={sum(words)/max(len(words),1):.0f}, "
        f"tables={sum(1 for c in all_chunks if c.kind == 'table')}, parse+chunk={t_parse:.1f}s"
    )

    t1 = time.time()
    stats = build_index(all_chunks)
    print(f"index: {stats} in {time.time() - t1:.1f}s")
    print(f"total ingest: {time.time() - t0:.1f}s")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="citesure.ingest.cli")
    sub = p.add_subparsers(dest="cmd", required=True)

    pp = sub.add_parser("parse")
    pp.add_argument("--doc", required=True)
    pp.add_argument("--page", type=int, default=None)
    pp.add_argument("--limit", type=int, default=40)
    pp.set_defaults(func=cmd_parse)

    pc = sub.add_parser("chunk")
    pc.add_argument("--doc", required=True)
    pc.add_argument("--limit", type=int, default=20)
    pc.set_defaults(func=cmd_chunk)

    pa = sub.add_parser("all")
    pa.set_defaults(func=cmd_all)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
