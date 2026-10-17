"""Download the CiteSure corpus PDFs listed in data/corpus_manifest.yaml.

Plain HTTPS GET of the official NIST URLs only. Respects the project's terms
policy: no scraping beyond the listed files, a User-Agent that identifies the
project, skip-if-exists, and SHA-256 + page-count recorded back into the
manifest after a real download (never guessed).

Usage:  python scripts/download_corpus.py
"""

from __future__ import annotations

import hashlib
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx
import pdfplumber
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MANIFEST = PROJECT_ROOT / "data" / "corpus_manifest.yaml"
RAW_DIR = PROJECT_ROOT / "data" / "raw"

USER_AGENT = "CiteSure-demo/0.1 (public-document research demo; +https://github.com/citesure-demo)"


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def page_count_of(path: Path) -> int:
    with pdfplumber.open(path) as pdf:
        return len(pdf.pages)


def download(url: str, dest: Path) -> None:
    tmp = dest.with_suffix(".part")
    with httpx.stream("GET", url, headers={"User-Agent": USER_AGENT}, follow_redirects=True, timeout=120) as r:
        r.raise_for_status()
        with tmp.open("wb") as fh:
            for chunk in r.iter_bytes():
                fh.write(chunk)
    tmp.replace(dest)


def main() -> int:
    manifest = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    docs = manifest["documents"]
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    changed = False

    for entry in docs:
        dest = RAW_DIR / entry["filename"]
        if dest.exists() and entry.get("sha256"):
            print(f"skip (exists): {entry['filename']}  sha256={entry['sha256'][:12]}…")
            continue
        print(f"downloading: {entry['url']}")
        download(entry["url"], dest)
        digest = sha256_of(dest)
        pages = page_count_of(dest)
        entry["sha256"] = digest
        entry["pages"] = pages
        entry["downloaded_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        changed = True
        print(f"  ok: {entry['filename']}  pages={pages}  sha256={digest[:16]}…")

    if changed:
        MANIFEST.write_text(
            yaml.safe_dump(manifest, sort_keys=False, allow_unicode=True, width=100),
            encoding="utf-8",
        )
        print(f"manifest updated: {MANIFEST}")
    else:
        print("manifest already complete; nothing written")

    total_pages = sum(e.get("pages") or 0 for e in docs)
    print(f"total pages: {total_pages}")
    if not (250 <= total_pages <= 450):
        print("WARNING: total pages outside the 250-450 target range from IDEATION section 2.1")
    return 0


if __name__ == "__main__":
    sys.exit(main())
