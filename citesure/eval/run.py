"""One-command eval runner.

  python -m citesure.eval.run                       # full pipeline, all splits, judged
  python -m citesure.eval.run --mode vector --split test
  python -m citesure.eval.run --retrieval-only      # no LLM calls
  python -m citesure.eval.run --calibrate           # sweep decline_threshold on the dev split (no LLM)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from citesure.answer.verify import verify_quote
from citesure.config import PROJECT_ROOT, load_settings
from citesure.eval import metrics as M
from citesure.eval.report import write_report
from citesure.qa import QA

QUESTIONS = PROJECT_ROOT / "eval" / "questions.jsonl"


def load_questions(path: Path = QUESTIONS, split: str = "all") -> list[dict[str, Any]]:
    qs = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if split != "all":
        qs = [q for q in qs if q.get("split") == split]
    return qs


def _git_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], cwd=PROJECT_ROOT, text=True, stderr=subprocess.DEVNULL
        ).strip()
    except Exception:
        return "unknown"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def header(settings, mode: str, split: str, n_unverified: int, extra: dict | None = None) -> dict[str, Any]:
    manifest = yaml.safe_load(settings.manifest_path.read_text(encoding="utf-8"))
    return {
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "git_commit": _git_commit(),
        "mode": mode,
        "split": split,
        "answer_model": settings.answer_model,
        "judge_model": settings.judge_model,
        "provider": settings.provider,
        "settings": {k: settings.raw.get(k) for k in ("retrieval", "chunking", "embeddings", "reranker", "answer")},
        "corpus_sha256": {d["doc_id"]: d["sha256"] for d in manifest["documents"]},
        "eval_file_sha256": _sha256(QUESTIONS),
        "questions_not_verified_by_human": n_unverified,
        **(extra or {}),
    }


def run_eval(
    mode: str | None = None,
    split: str = "all",
    judge: bool = True,
    retrieval_only: bool = False,
    qa: QA | None = None,
    questions: list[dict[str, Any]] | None = None,
    verbose: bool = True,
) -> dict[str, Any]:
    settings = load_settings()
    mode = mode or settings.retrieval.get("mode", "hybrid_rerank")
    all_q = questions if questions is not None else load_questions(split="all")
    qs = [q for q in all_q if split == "all" or q.get("split") == split]
    qa = qa or QA()
    chunks = qa.retriever.index.chunks

    judge_obj = None
    if judge and not retrieval_only:
        from citesure.eval.judge import Judge
        from citesure.llm import get_provider

        judge_obj = Judge(get_provider(settings.judge_model), settings.judge_model)

    results: list[dict[str, Any]] = []
    for i, q in enumerate(qs, 1):
        golds = q.get("gold_sources") or []
        if retrieval_only:
            t0 = time.perf_counter()
            retrieved, timings = qa.retriever.retrieve(q["question"], mode)
            qa.last = {"retrieved": retrieved, "gated": False}
            resp = None
            timings = {**timings, "total": (time.perf_counter() - t0) * 1000}
        else:
            resp = qa.ask(q["question"], mode)
            retrieved = qa.last["retrieved"]
            timings = resp.timings_ms
        rchunks = [chunks[r.chunk_id] for r in retrieved]
        rank = M.first_gold_rank(rchunks, golds) if q["answerable"] else None
        r: dict[str, Any] = {
            "id": q["id"], "question": q["question"], "category": q.get("category"),
            "split": q.get("split"), "answerable": q["answerable"], "mode": mode,
            "retrieved_chunk_ids": [c.chunk_id for c in rchunks],
            "top_rerank_score": retrieved[0].rerank_score if retrieved else None,
            "gold_rank": rank, "hit@1": rank == 1, "hit@5": rank is not None and rank <= 5,
            "timings_ms": timings,
            "status": resp.status if resp else "n/a",
            "gated": qa.last.get("gated", False),
        }
        if resp is not None:
            cost = resp.cost_usd
            r.update(
                answer=resp.answer, clarifying_question=resp.clarifying_question,
                citations=[c.model_dump() for c in resp.citations], usage=resp.usage, cost_usd=cost,
                n_citations=len(resp.citations),
                n_citations_verified=sum(
                    1 for c in resp.citations
                    if c.chunk_id in chunks and verify_quote(chunks[c.chunk_id], c.quote)
                ),
                cited_gold_page=any(c.doc_id == g["doc_id"] and c.page == int(g["page"]) for c in resp.citations for g in golds),
                faithful=None, correct=None,
            )
            if judge_obj and resp.status == "answered":
                before = judge_obj.cost_usd
                f, why = judge_obj.faithfulness(resp, chunks)
                r["faithful"], r["faithful_reason"] = f, why
                if q["answerable"]:
                    c_, why2 = judge_obj.correctness(q["question"], q["gold_answer"], resp)
                    r["correct"], r["correct_reason"] = c_, why2
                r["judge_cost_usd"] = judge_obj.cost_usd - before
            elif q["answerable"]:
                r["correct"] = 0  # a decline on an answerable question counts as incorrect
        results.append(r)
        if verbose:
            print(f"[{i}/{len(qs)}] {q['id']} {mode} -> {r['status']} rank={rank} {timings.get('total', 0):.0f}ms", flush=True)

    unverified = sum(1 for q in all_q if not q.get("verified_by_human"))
    summary = M.summarize(results)
    # for retrieval-only runs the end-to-end fields are meaningless
    if retrieval_only:
        summary = {k: v for k, v in summary.items() if k.startswith("retrieval_") or k.startswith("n_") or k.startswith("latency")}
    return {"header": header(settings, mode, split, unverified, {"retrieval_only": retrieval_only}),
            "summary": summary, "results": results}


def save(run: dict[str, Any], prefix: str = "eval") -> Path:
    settings = load_settings()
    settings.reports_dir.mkdir(parents=True, exist_ok=True)
    ts = run["header"]["timestamp"].replace(":", "").replace("-", "")
    base = settings.reports_dir / f"{prefix}_{ts}"
    base.with_suffix(".json").write_text(json.dumps(run, indent=2), encoding="utf-8")
    base.with_suffix(".md").write_text(write_report(run), encoding="utf-8")
    return base


def calibrate(verbose: bool = True) -> dict[str, Any]:
    """Sweep decline_threshold over dev-split top rerank scores (no LLM calls).
    Objective: (unanswerable below threshold) + (answerable at/above threshold)."""
    qa = QA()
    dev = load_questions(split="dev")
    rows = []
    for q in dev:
        retrieved, _ = qa.retriever.retrieve(q["question"], "hybrid_rerank")
        rows.append((q["answerable"], retrieved[0].rerank_score if retrieved else -99.0))
    cands = sorted({round(s, 3) for _, s in rows})
    best = None
    sweep = []
    for thr in [min(cands) - 1] + cands:
        score = sum(1 for a, s in rows if (not a and s < thr) or (a and s >= thr))
        sweep.append((thr, score))
        # prefer the lowest threshold among ties (least aggressive gate)
        if best is None or score > best[1]:
            best = (thr, score)
    out = {"best_threshold": best[0], "dev_objective": best[1], "dev_n": len(rows),
           "baseline_objective_no_gate": sum(1 for a, _ in rows if a), "sweep": sweep}
    if verbose:
        print(json.dumps({k: v for k, v in out.items() if k != "sweep"}, indent=2))
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="citesure.eval.run")
    ap.add_argument("--mode", default=None, help="vector|bm25|hybrid|hybrid_rerank (default: settings.yaml)")
    ap.add_argument("--split", default="all", choices=["all", "dev", "test"])
    ap.add_argument("--no-judge", action="store_true")
    ap.add_argument("--retrieval-only", action="store_true")
    ap.add_argument("--calibrate", action="store_true")
    a = ap.parse_args(argv)
    if a.calibrate:
        calibrate()
        return 0
    run = run_eval(a.mode, a.split, judge=not a.no_judge, retrieval_only=a.retrieval_only)
    base = save(run, "eval_retrieval" if a.retrieval_only else "eval")
    print(f"\nwrote {base.with_suffix('.md')} and .json")
    print(json.dumps(run["summary"], indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
