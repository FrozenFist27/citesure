"""Eval metrics. Pure functions over per-question result dicts (no I/O, no network)."""

from __future__ import annotations

import re
import statistics
from typing import Any

from citesure.answer.verify import norm_chars
from citesure.models import Chunk

_TOK = re.compile(r"\w+")


def _tokens(s: str) -> list[str]:
    return _TOK.findall(norm_chars(s).lower())


def _trigrams(toks: list[str]) -> set[tuple[str, ...]]:
    return {tuple(toks[i : i + 3]) for i in range(len(toks) - 2)}


def chunk_matches_gold(chunk: Chunk, gold: dict[str, Any], min_overlap: float = 0.5) -> bool:
    """A retrieved chunk matches a gold source iff it is from the same document, its page range
    contains the gold page, and it contains the gold passage (exact normalised substring, or at
    least `min_overlap` of the passage's word trigrams)."""
    if chunk.doc_id != gold["doc_id"]:
        return False
    if not (chunk.page_start <= int(gold["page"]) <= chunk.page_end):
        return False
    g = _tokens(gold["passage"])
    c = _tokens(chunk.text)
    gs = " ".join(g)
    if gs and gs in " ".join(c):
        return True
    gt = _trigrams(g)
    if not gt:
        return False
    return len(gt & _trigrams(c)) / len(gt) >= min_overlap


def first_gold_rank(chunks: list[Chunk], golds: list[dict[str, Any]]) -> int | None:
    """1-based rank of the first chunk matching any gold source, else None."""
    for i, ch in enumerate(chunks, 1):
        if any(chunk_matches_gold(ch, g) for g in golds):
            return i
    return None


def retrieval_metrics(ranks: list[int | None], k: int = 5) -> dict[str, float]:
    n = len(ranks)
    if n == 0:
        return {"n": 0, "hit@1": 0.0, "hit@5": 0.0, "mrr@5": 0.0}
    return {
        "n": n,
        "hit@1": sum(1 for r in ranks if r == 1) / n,
        "hit@5": sum(1 for r in ranks if r is not None and r <= k) / n,
        "mrr@5": sum(1 / r for r in ranks if r is not None and r <= k) / n,
    }


def _pct(vals: list[float], p: float) -> float:
    if not vals:
        return 0.0
    s = sorted(vals)
    idx = min(len(s) - 1, max(0, int(round(p * (len(s) - 1)))))
    return s[idx]


def summarize(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate per-question results into the headline metrics (IDEATION 8.2)."""
    ans = [r for r in results if r["answerable"]]
    unans = [r for r in results if not r["answerable"]]
    answered = [r for r in results if r["status"] == "answered"]
    answered_ans = [r for r in ans if r["status"] == "answered"]

    out: dict[str, Any] = {"n_questions": len(results), "n_answerable": len(ans), "n_unanswerable": len(unans)}
    out.update({f"retrieval_{k}": v for k, v in retrieval_metrics([r["gold_rank"] for r in ans]).items()})

    n_cit = sum(r.get("n_citations", 0) for r in results)
    n_ver = sum(r.get("n_citations_verified", 0) for r in results)
    out["quote_verification_rate"] = (n_ver / n_cit) if n_cit else None
    out["citation_page_accuracy"] = (
        sum(1 for r in answered_ans if r.get("cited_gold_page")) / len(answered_ans) if answered_ans else None
    )

    judged = [r for r in answered if r.get("faithful") is not None]
    out["faithfulness"] = (sum(r["faithful"] for r in judged) / len(judged)) if judged else None
    out["n_faithfulness_judged"] = len(judged)
    corr = [r for r in ans if r.get("correct") is not None]
    out["answer_correctness"] = (sum(r["correct"] for r in corr) / len(corr)) if corr else None

    out["correct_declines"] = sum(1 for r in unans if r["status"] in ("declined", "clarify"))
    out["unanswerable_total"] = len(unans)
    out["false_decline_rate"] = (
        sum(1 for r in ans if r["status"] in ("declined", "clarify")) / len(ans) if ans else None
    )

    lat = [r["timings_ms"].get("total", 0.0) for r in results if r.get("timings_ms")]
    out["latency_ms_p50"] = statistics.median(lat) if lat else None
    out["latency_ms_p95"] = _pct(lat, 0.95) if lat else None
    stage = {}
    for key in ("retrieve", "rerank", "llm", "verify"):
        vals = [r["timings_ms"].get(key, 0.0) for r in results if r.get("timings_ms")]
        stage[key] = round(sum(vals) / len(vals), 1) if vals else None
    out["latency_ms_mean_by_stage"] = stage

    costs = [r["cost_usd"] for r in results if r.get("cost_usd") is not None]
    out["cost_per_question_usd"] = (sum(costs) / len(results)) if costs and results else None
    out["cost_total_usd"] = sum(costs) if costs else None
    out["judge_cost_total_usd"] = sum(r.get("judge_cost_usd") or 0.0 for r in results) or None
    out["llm_calls_skipped_by_gate"] = sum(1 for r in results if r.get("gated"))
    return out
