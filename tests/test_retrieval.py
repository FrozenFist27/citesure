"""M5: retrieval on a tiny synthetic index with a fake (bag-of-words hash) embedder."""

from __future__ import annotations

import zlib

import numpy as np
import pytest

from citesure.ingest import index as index_mod
from citesure.models import Chunk
from citesure.retrieval import vector as vector_mod
from citesure.retrieval.fusion import rrf
from citesure.retrieval.pipeline import Retriever

DIM = 64


class FakeEmbedder:
    """Deterministic bag-of-words hashing embedder (stable across processes)."""

    def encode(self, texts, normalize_embeddings=True, convert_to_numpy=True, **kw):
        out = np.zeros((len(texts), DIM), dtype=np.float32)
        for i, t in enumerate(texts):
            for w in t.lower().split():
                out[i, zlib.crc32(w.encode()) % DIM] += 1.0
        n = np.linalg.norm(out, axis=1, keepdims=True)
        return out / np.where(n == 0, 1, n)


def _chunk(i, title, text):
    return Chunk(chunk_id=f"d:{i}:001", doc_id="d", doc_title="Doc", section_path=title,
                 page_start=i, page_end=i, text=text, context_text=f"Doc > {title}\n{text}",
                 n_words=len(text.split()))


@pytest.fixture()
def retriever(tmp_path, monkeypatch):
    monkeypatch.setattr(index_mod, "_get_embedder", lambda name: FakeEmbedder())
    monkeypatch.setattr(vector_mod, "get_embedder", lambda name=None: FakeEmbedder())
    chunks = [
        _chunk(1, "Passwords", "Verifiers shall require passwords to be at least 15 characters long."),
        _chunk(2, "Incident", "Organizations should prepare incident response plans and exercises."),
        _chunk(3, "Audit", "Audit records shall be retained and reviewed for suspicious activity."),
        _chunk(4, "Supply", "Supply chain risk management requires supplier assessments."),
    ]
    index_mod.build_index(chunks, index_dir=tmp_path)
    return Retriever(index=index_mod.Index(tmp_path))


def test_rrf_is_deterministic_and_rewards_agreement():
    out = rrf([["a", "b", "c"], ["b", "a", "d"]], k=60)
    ids = [c for c, _ in out]
    assert ids[:2] == ["a", "b"]  # tie on score -> first appearance wins
    assert set(ids) == {"a", "b", "c", "d"}
    assert rrf([["a", "b"], ["b", "a"]]) == rrf([["a", "b"], ["b", "a"]])
    # an item ranked high in both lists beats an item high in only one
    assert [c for c, _ in rrf([["x", "y"], ["z", "x"]])][0] == "x"


def test_bm25_mode_finds_exact_term(retriever):
    res, _ = retriever.retrieve("incident response plans", mode="bm25", final_k=2)
    assert res[0].chunk_id == "d:2:001"
    assert res[0].bm25_rank == 1


def test_vector_mode_ranks_overlap_first(retriever):
    res, _ = retriever.retrieve("passwords characters long", mode="vector", final_k=2)
    assert res[0].chunk_id == "d:1:001"
    assert res[0].vector_rank == 1


def test_hybrid_merges_both(retriever):
    res, t = retriever.retrieve("audit records review", mode="hybrid", final_k=3)
    assert res[0].chunk_id == "d:3:001"
    assert res[0].rrf_rank == 1
    assert "retrieve" in t


def test_unknown_mode_raises(retriever):
    with pytest.raises(ValueError):
        retriever.retrieve("x", mode="nope")


def test_hybrid_rerank_uses_reranker(retriever, monkeypatch):
    import citesure.retrieval.pipeline as pl

    def fake_rerank(index, query, ids):
        return sorted(((c, 1.0 if c == "d:4:001" else -1.0) for c in ids), key=lambda kv: -kv[1])

    monkeypatch.setattr(pl, "rerank", fake_rerank)
    res, t = retriever.retrieve("audit records", mode="hybrid_rerank", final_k=2)
    assert res[0].chunk_id == "d:4:001" and res[0].rerank_score == 1.0
    assert "rerank" in t
