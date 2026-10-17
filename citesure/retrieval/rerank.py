"""Cross-encoder re-ranking (ms-marco-MiniLM-L-6-v2, local CPU)."""

from __future__ import annotations

from citesure.config import load_settings
from citesure.ingest.index import Index

_RERANKER = None


def get_reranker():
    global _RERANKER
    if _RERANKER is None:
        from sentence_transformers import CrossEncoder

        name = load_settings().reranker.get("model_name", "cross-encoder/ms-marco-MiniLM-L-6-v2")
        _RERANKER = CrossEncoder(name, max_length=512)
    return _RERANKER


def rerank(index: Index, query: str, chunk_ids: list[str]) -> list[tuple[str, float]]:
    """Return (chunk_id, score) sorted by cross-encoder score, best first."""
    if not chunk_ids:
        return []
    model = get_reranker()
    pairs = [(query, index.chunks[c].context_text) for c in chunk_ids]
    scores = model.predict(pairs, batch_size=16, show_progress_bar=False)
    out = sorted(zip(chunk_ids, (float(s) for s in scores)), key=lambda kv: -kv[1])
    return out
