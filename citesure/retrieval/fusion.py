"""Reciprocal Rank Fusion."""

from __future__ import annotations


def rrf(rankings: list[list[str]], k: int = 60) -> list[tuple[str, float]]:
    """Fuse ranked id lists. score(id) = sum 1/(k + rank), rank starting at 1.
    Ties broken by first appearance order, so the result is deterministic."""
    scores: dict[str, float] = {}
    first_seen: dict[str, int] = {}
    n = 0
    for ranking in rankings:
        for pos, cid in enumerate(ranking, start=1):
            scores[cid] = scores.get(cid, 0.0) + 1.0 / (k + pos)
            if cid not in first_seen:
                first_seen[cid] = n
                n += 1
    return sorted(scores.items(), key=lambda kv: (-kv[1], first_seen[kv[0]]))
