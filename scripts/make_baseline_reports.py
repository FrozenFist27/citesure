"""Turn the latest raw eval/compare/ablation JSON into the committed baseline reports.

  python scripts/make_baseline_reports.py <eval.json> <compare.json> <ablation.json>

Only re-formats numbers that already exist in the JSON files from real runs.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from citesure.eval import metrics as M  # noqa: E402
from citesure.eval.report import metrics_table, write_compare, write_report  # noqa: E402


def main(eval_p: str, cmp_p: str | None = None, abl_p: str | None = None) -> None:
    rep = ROOT / "reports"
    run = json.loads(Path(eval_p).read_text(encoding="utf-8"))
    results = run["results"]
    parts = {sp: M.summarize([r for r in results if sp == "all" or r["split"] == sp]) for sp in ("test", "dev", "all")}

    md = write_report(run).split("## Per-question results")
    h = run["header"]
    head = [
        f"# CiteSure eval report (baseline: mode={h['mode']}, one command: `python -m citesure.eval.run`)",
        "",
        f"- Timestamp: {h['timestamp']}  |  git commit: `{h['git_commit']}`",
        f"- Answer model: `{h['answer_model']}`  |  judge model: `{h['judge_model']}`",
        f"- Settings: {json.dumps(h['settings']['retrieval'])}",
        f"- Eval file sha256: `{h['eval_file_sha256'][:16]}...`  |  corpus sha256: " +
        ", ".join(f"{k}=`{v[:8]}`" for k, v in h["corpus_sha256"].items()),
        f"- Questions not verified by a human: {h['questions_not_verified_by_human']} of 50 "
        "(drafted by an LLM, gold passages verified programmatically against the PDF text; see eval/README.md)",
        "",
    ]
    out = list(head)
    for sp, title in (("test", "Test split (headline, 34 questions)"), ("dev", "Dev split (16 questions, used to calibrate the gate)"),
                      ("all", "All 50 questions")):
        out += [f"## {title}", ""] + metrics_table(parts[sp]) + [""]
    out += ["## Per-question results" + md[1]]
    (rep / "eval_baseline.md").write_text("\n".join(out), encoding="utf-8")
    (rep / "eval_baseline.json").write_text(json.dumps({**run, "summaries": parts}, indent=2), encoding="utf-8")

    if not cmp_p or not abl_p:
        print("wrote reports/eval_baseline.* (compare reports left unchanged)")
        return
    cmp_ = json.loads(Path(cmp_p).read_text(encoding="utf-8"))
    cmp_.update(json.loads(Path(abl_p).read_text(encoding="utf-8")))
    note = (
        "Same 50 questions, same answer and judge model (`claude-haiku-5-5`); only retrieval mode (or the "
        "relevance gate) changes. Headline = test split. `hybrid_rerank` runs with the dev-calibrated gate "
        "(threshold 0.1); the default config has the gate off; `hybrid_rerank:nogate` is the same pipeline with the gate disabled. LLM output is "
        "not perfectly deterministic, so small differences between this table and `eval_baseline.md` "
        "(a separate run of the same final configuration) are run-to-run noise."
    )
    (rep / "compare_baseline.md").write_text(write_compare(cmp_, "CiteSure before/after: retrieval modes and gate", note), encoding="utf-8")
    (rep / "compare_baseline.json").write_text(json.dumps(cmp_, indent=2, default=str), encoding="utf-8")
    print("wrote reports/eval_baseline.* and reports/compare_baseline.*")


if __name__ == "__main__":
    main(*sys.argv[1:4])
