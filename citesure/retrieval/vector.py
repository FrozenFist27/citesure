"""Dense retrieval: bge-small embeddings, cosine similarity via dot product."""

from __future__ import annotations

import numpy as np

from citesure.config import load_settings
from citesure.ingest.index import Index

_EMBEDDER = None
_EMBEDDER_NAME = None


def get_embedder(model_name: str | None = None):
    global _EMBEDDER, _EMBEDDER_NAME
    name = model_name or load_settings().embeddings.get("model_name", "BAAI/bge-small-en-v1.5")
    if _EMBEDDER is None or _EMBEDDER_NAME != name:
        from sentence_transformers import SentenceTransformer

        _EMBEDDER = SentenceTransformer(name)
        _EMBEDDER_NAME = name
    return _EMBEDDER


def embed_query(query: str) -> np.ndarray:
    prefix = load_settings().embeddings.get("query_prefix", "")
    v = get_embedder().encode([prefix + query], normalize_embeddings=True, convert_to_numpy=True)
    return np.asarray(v[0], dtype=np.float32)


def vector_search(
    index: Index, query: str, k: int = 20, qvec: np.ndarray | None = None
) -> list[tuple[str, float]]:
    if index.embeddings is None:
        return []
    q = qvec if qvec is not None else embed_query(query)
    sims = index.embeddings @ q
    top = np.argsort(-sims)[:k]
    return [(index.embed_ids[i], float(sims[i])) for i in top]
