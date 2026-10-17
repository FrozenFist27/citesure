"""Relevance gate: decline without an LLM call when retrieval is clearly off-topic."""

from __future__ import annotations

from citesure.models import RetrievedChunk


def should_decline(retrieved: list[RetrievedChunk], threshold: float) -> bool:
    """True if there is nothing retrieved or the best cross-encoder score is below threshold.
    A threshold of 0.0 with rerank scores is a real cut-off; use a very negative value to disable."""
    if not retrieved:
        return True
    best = retrieved[0].rerank_score
    if best is None:  # no reranker in this mode: gate cannot judge, let the LLM decide
        return False
    return best < threshold
