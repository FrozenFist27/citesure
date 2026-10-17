"""Build the CiteSure retrieval index.

Outputs (all under index/, git-ignored):
- chunks.sqlite   chunk metadata + text (schema: IDEATION 5.1)
- bm25.pkl        pickled BM25Okapi over tokenised context_text
- embeddings.npy  L2-normalised bge-small matrix, row i <-> chunk_ids.json[i]
- chunk_ids.json  ordered chunk ids for the embedding matrix

Embeddings run locally (no API). The bge model card's instruction prefix is
applied to QUERIES at retrieval time, not to these passages.
"""

from __future__ import annotations

import json
import pickle
import re
import sqlite3
import time
from pathlib import Path
from typing import Any

import numpy as np
from rank_bm25 import BM25Okapi

from citesure.config import load_settings
from citesure.models import Chunk

SCHEMA = """
CREATE TABLE IF NOT EXISTS chunks (
    chunk_id    TEXT PRIMARY KEY,
    doc_id      TEXT NOT NULL,
    doc_title   TEXT NOT NULL,
    section_path TEXT NOT NULL,
    page_start  INTEGER NOT NULL,
    page_end    INTEGER NOT NULL,
    kind        TEXT NOT NULL,
    text        TEXT NOT NULL,
    context_text TEXT NOT NULL,
    n_words     INTEGER NOT NULL,
    page_offsets TEXT NOT NULL DEFAULT '[]'
);
CREATE INDEX IF NOT EXISTS idx_chunks_doc ON chunks(doc_id);
"""

RE_TOKEN = re.compile(r"\w+", re.UNICODE)


def tokenize(text: str) -> list[str]:
    return [t.lower() for t in RE_TOKEN.findall(text)]


def _get_embedder(model_name: str):
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(model_name)


def build_index(
    chunks: list[Chunk],
    index_dir: str | Path | None = None,
    embed_model_name: str | None = None,
) -> dict[str, Any]:
    settings = load_settings()
    index_dir = Path(index_dir or settings.index_dir)
    index_dir.mkdir(parents=True, exist_ok=True)
    embed_model_name = embed_model_name or settings.embeddings.get(
        "model_name", "BAAI/bge-small-en-v1.5"
    )

    t0 = time.time()
    db_path = index_dir / "chunks.sqlite"
    if db_path.exists():
        db_path.unlink()
    con = sqlite3.connect(db_path)
    con.executescript(SCHEMA)
    con.executemany(
        "INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        [
            (
                c.chunk_id,
                c.doc_id,
                c.doc_title,
                c.section_path,
                c.page_start,
                c.page_end,
                c.kind,
                c.text,
                c.context_text,
                c.n_words,
                json.dumps(c.page_offsets),
            )
            for c in chunks
        ],
    )
    con.commit()
    con.close()
    t_sqlite = time.time() - t0

    # BM25 over tokenised context_text
    t1 = time.time()
    corpus_tokens = [tokenize(c.context_text) for c in chunks]
    bm25 = BM25Okapi(corpus_tokens)
    with (index_dir / "bm25.pkl").open("wb") as fh:
        pickle.dump({"bm25": bm25, "chunk_ids": [c.chunk_id for c in chunks]}, fh)
    t_bm25 = time.time() - t1

    # embeddings (local model, L2-normalised)
    t2 = time.time()
    embedder = _get_embedder(embed_model_name)
    vectors = embedder.encode(
        [c.context_text for c in chunks],
        batch_size=64,
        show_progress_bar=False,
        convert_to_numpy=True,
        normalize_embeddings=True,
    )
    vectors = np.asarray(vectors, dtype=np.float32)
    np.save(index_dir / "embeddings.npy", vectors)
    (index_dir / "chunk_ids.json").write_text(
        json.dumps([c.chunk_id for c in chunks]), encoding="utf-8"
    )
    t_embed = time.time() - t2

    return {
        "n_chunks": len(chunks),
        "dim": int(vectors.shape[1]) if vectors.ndim == 2 else 0,
        "seconds_sqlite": round(t_sqlite, 2),
        "seconds_bm25": round(t_bm25, 2),
        "seconds_embed": round(t_embed, 2),
        "seconds_total": round(time.time() - t0, 2),
        "index_dir": str(index_dir),
    }


class Index:
    """Loaded retrieval index: chunks by id, BM25, embedding matrix."""

    def __init__(self, index_dir: str | Path | None = None):
        settings = load_settings()
        self.index_dir = Path(index_dir or settings.index_dir)
        self.chunks: dict[str, Chunk] = {}
        self.order: list[str] = []
        self.bm25: BM25Okapi | None = None
        self.bm25_ids: list[str] = []
        self.embeddings: np.ndarray | None = None
        self.embed_ids: list[str] = []
        self._load()

    def _load(self) -> None:
        db_path = self.index_dir / "chunks.sqlite"
        if not db_path.exists():
            raise FileNotFoundError(
                f"index not found at {self.index_dir} - run ingest first "
                "(python -m citesure.ingest.cli all)"
            )
        con = sqlite3.connect(db_path)
        con.row_factory = sqlite3.Row
        for row in con.execute("SELECT * FROM chunks"):
            c = Chunk(
                chunk_id=row["chunk_id"],
                doc_id=row["doc_id"],
                doc_title=row["doc_title"],
                section_path=row["section_path"],
                page_start=row["page_start"],
                page_end=row["page_end"],
                kind=row["kind"],
                text=row["text"],
                context_text=row["context_text"],
                n_words=row["n_words"],
                page_offsets=json.loads(row["page_offsets"]),
            )
            self.chunks[c.chunk_id] = c
            self.order.append(c.chunk_id)
        con.close()

        bm25_path = self.index_dir / "bm25.pkl"
        if bm25_path.exists():
            with bm25_path.open("rb") as fh:
                payload = pickle.load(fh)
            self.bm25 = payload["bm25"]
            self.bm25_ids = payload["chunk_ids"]

        emb_path = self.index_dir / "embeddings.npy"
        ids_path = self.index_dir / "chunk_ids.json"
        if emb_path.exists() and ids_path.exists():
            self.embeddings = np.load(emb_path)
            self.embed_ids = json.loads(ids_path.read_text(encoding="utf-8"))

    def get(self, chunk_id: str) -> Chunk | None:
        return self.chunks.get(chunk_id)
