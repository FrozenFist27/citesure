"""Retrieval pipeline with switchable modes: vector | bm25 | hybrid | hybrid_rerank.

CLI: python -m citesure.retrieval.pipeline "question" [--mode hybrid_rerank]
"""

from __future__ import annotations

import argparse
import time

from citesure.config import load_settings
from citesure.ingest.index import Index
from citesure.models import RetrievedChunk
from citesure.retrieval.bm25 import bm25_search
from citesure.retrieval.fusion import rrf
from citesure.retrieval.rerank import rerank
from citesure.retrieval.vector import embed_query, vector_search

MODES = ("vector", "bm25", "hybrid", "hybrid_rerank")


class Retriever:
    def __init__(self, index: Index | None = None, settings=None):
        self.settings = settings or load_settings()
        self.index = index or Index()

    def retrieve(
        self, query: str, mode: str | None = None, final_k: int | None = None
    ) -> tuple[list[RetrievedChunk], dict[str, float]]:
        cfg = self.settings.retrieval
        mode = mode or cfg.get("mode", "hybrid_rerank")
        if mode not in MODES:
            raise ValueError(f"unknown retrieval mode {mode!r}; expected one of {MODES}")
        final_k = final_k or int(cfg.get("final_k", 5))
        bm25_k = int(cfg.get("bm25_k", 20))
        vector_k = int(cfg.get("vector_k", 20))
        rrf_k = int(cfg.get("rrf_k", 60))
        top_n = int(cfg.get("rerank_top_n", 20))
        timings: dict[str, float] = {}

        t0 = time.perf_counter()
        bm: list[tuple[str, float]] = []
        vec: list[tuple[str, float]] = []
        if mode in ("bm25", "hybrid", "hybrid_rerank"):
            bm = bm25_search(self.index, query, bm25_k)
        if mode in ("vector", "hybrid", "hybrid_rerank"):
            qv = embed_query(query)
            vec = vector_search(self.index, query, vector_k, qvec=qv)
        timings["retrieve"] = (time.perf_counter() - t0) * 1000

        bm_rank = {c: i for i, (c, _) in enumerate(bm, 1)}
        vec_rank = {c: i for i, (c, _) in enumerate(vec, 1)}

        if mode == "bm25":
            fused = [(c, s) for c, s in bm]
        elif mode == "vector":
            fused = [(c, s) for c, s in vec]
        else:
            fused = rrf([[c for c, _ in bm], [c for c, _ in vec]], k=rrf_k)
        rrf_rank = {c: i for i, (c, _) in enumerate(fused, 1)}

        out: list[RetrievedChunk] = []
        timings["rerank"] = 0.0
        if mode == "hybrid_rerank":
            t1 = time.perf_counter()
            cand = [c for c, _ in fused[:top_n]]
            ranked = rerank(self.index, query, cand)
            timings["rerank"] = (time.perf_counter() - t1) * 1000
            for c, s in ranked[:final_k]:
                out.append(
                    RetrievedChunk(
                        chunk_id=c, score=s, rerank_score=s,
                        bm25_rank=bm_rank.get(c), vector_rank=vec_rank.get(c),
                        rrf_rank=rrf_rank.get(c),
                    )
                )
        else:
            for c, s in fused[:final_k]:
                out.append(
                    RetrievedChunk(
                        chunk_id=c, score=s,
                        bm25_rank=bm_rank.get(c), vector_rank=vec_rank.get(c),
                        rrf_rank=rrf_rank.get(c),
                    )
                )
        return out, timings


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("question")
    ap.add_argument("--mode", default=None)
    args = ap.parse_args()
    r = Retriever()
    res, t = r.retrieve(args.question, args.mode)
    for i, rc in enumerate(res, 1):
        c = r.index.chunks[rc.chunk_id]
        print(f"{i}. {rc.score:.3f} {c.doc_id} p{c.page_start} {c.section_path[:70]!r}\n   {c.text[:140]!r}")
    print({k: round(v, 1) for k, v in t.items()})


if __name__ == "__main__":
    main()
