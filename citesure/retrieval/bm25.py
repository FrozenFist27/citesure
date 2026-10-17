"""BM25 keyword retrieval over the pickled BM25Okapi index."""

from __future__ import annotations

import numpy as np

from citesure.ingest.index import Index, tokenize


def bm25_search(index: Index, query: str, k: int = 20) -> list[tuple[str, float]]:
    if index.bm25 is None:
        return []
    scores = np.asarray(index.bm25.get_scores(tokenize(query)), dtype=np.float32)
    if scores.size == 0:
        return []
    top = np.argsort(-scores)[:k]
    return [(index.bm25_ids[i], float(scores[i])) for i in top if scores[i] > 0]
