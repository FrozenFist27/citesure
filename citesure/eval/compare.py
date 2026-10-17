"""Before/after comparison across retrieval modes (full pipeline, same questions).

  python -m citesure.eval.compare [--modes vector hybrid hybrid_rerank]
"""

from __future__ import annotations

import argparse
import json
import sys

from citesure.config import load_settings
from citesure.eval import metrics as M
from citesure.eval.report import write_compare
from citesure.eval.run import header, load_questions, run_eval
from citesure.qa import QA


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="citesure.eval.compare")
    ap.add_argument("--modes", nargs="+", default=["vector", "hybrid", "hybrid_rerank"])
    ap.add_argument("--no-judge", action="store_true")
    ap.add_argument("--prefix", default="compare")
    a = ap.parse_args(argv)

    settings = load_settings()
    qa = QA()
    questions = load_questions()
    runs = {}
    for mode in a.modes:
        print(f"=== mode {mode}", flush=True)
        real_mode = mode.split(":")[0]
        saved = settings.raw["retrieval"]["decline_threshold"]
        if mode.endswith(":nogate"):  # ablation: relevance gate disabled, LLM decides alone
            settings.raw["retrieval"]["decline_threshold"] = -99.0
        try:
            full = run_eval(real_mode, "all", judge=not a.no_judge, qa=qa, questions=questions, verbose=False)
        finally:
            settings.raw["retrieval"]["decline_threshold"] = saved
        full["header"]["mode"] = mode
        by_split = {sp: M.summarize([r for r in full["results"] if sp == "all" or r["split"] == sp])
                    for sp in ("test", "dev", "all")}
        runs[mode] = {"header": full["header"], "summaries": by_split, "results": full["results"]}
        print(json.dumps(by_split["test"], indent=1, default=str)[:600], flush=True)

    first = next(iter(runs.values()))
    note = ("Same questions, same answer/judge model, only the retrieval mode changes. "
            "Headline = test split. Full per-question results are in the JSON file.")
    md = write_compare(runs, "CiteSure before/after: retrieval modes", note)
    settings.reports_dir.mkdir(parents=True, exist_ok=True)
    ts = first["header"]["timestamp"].replace(":", "").replace("-", "")
    (settings.reports_dir / f"{a.prefix}_{ts}.md").write_text(md, encoding="utf-8")
    (settings.reports_dir / f"{a.prefix}_{ts}.json").write_text(json.dumps(runs, indent=2, default=str), encoding="utf-8")
    print(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
