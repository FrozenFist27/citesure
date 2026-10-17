"""Markdown rendering of eval runs and comparisons."""

from __future__ import annotations

from typing import Any


def pct(x: float | None, digits: int = 1) -> str:
    return "n/a" if x is None else f"{100 * x:.{digits}f}%"


def usd(x: float | None) -> str:
    return "n/a" if x is None else f"${x:.5f}"


def ms(x: float | None) -> str:
    return "n/a" if x is None else f"{x:,.0f} ms"


def metrics_table(s: dict[str, Any]) -> list[str]:
    lines = ["| Metric | Value |", "|---|---|"]
    lines.append(f"| Questions (answerable / unanswerable) | {s['n_questions']} ({s['n_answerable']} / {s['n_unanswerable']}) |")
    lines.append(f"| Retrieval hit rate @1 | {pct(s.get('retrieval_hit@1'))} |")
    lines.append(f"| Retrieval hit rate @5 | {pct(s.get('retrieval_hit@5'))} |")
    lines.append(f"| MRR@5 | {s.get('retrieval_mrr@5', 0):.3f} |")
    if "faithfulness" in s:
        lines.append(f"| Quote verification rate (guardrail) | {pct(s.get('quote_verification_rate'))} |")
        lines.append(f"| Citation page accuracy | {pct(s.get('citation_page_accuracy'))} |")
        lines.append(f"| Faithfulness (LLM judge, answered questions) | {pct(s.get('faithfulness'))} (n={s.get('n_faithfulness_judged')}) |")
        lines.append(f"| Answer correctness (answerable) | {pct(s.get('answer_correctness'))} |")
        lines.append(f"| Correct declines | {s['correct_declines']} / {s['unanswerable_total']} |")
        lines.append(f"| False decline rate (answerable) | {pct(s.get('false_decline_rate'))} |")
        lines.append(f"| Cost per question (answer model) | {usd(s.get('cost_per_question_usd'))} |")
        lines.append(f"| Total answer cost | {usd(s.get('cost_total_usd'))} |")
        lines.append(f"| Judge cost (reported separately) | {usd(s.get('judge_cost_total_usd'))} |")
    lines.append(f"| Latency p50 / p95 | {ms(s.get('latency_ms_p50'))} / {ms(s.get('latency_ms_p95'))} |")
    st = s.get("latency_ms_mean_by_stage") or {}
    if st:
        lines.append("| Mean latency by stage | " + ", ".join(f"{k} {v} ms" for k, v in st.items()) + " |")
    return lines


def write_report(run: dict[str, Any]) -> str:
    h, s = run["header"], run["summary"]
    L = [f"# CiteSure eval report ({h['mode']}, split={h['split']})", ""]
    L += [
        f"- Timestamp: {h['timestamp']}  |  git commit: `{h['git_commit']}`",
        f"- Answer model: `{h['answer_model']}`  |  judge model: `{h['judge_model']}`",
        f"- Eval file sha256: `{h['eval_file_sha256'][:16]}...`  |  questions not verified by a human: {h['questions_not_verified_by_human']}",
        "",
    ]
    if h["questions_not_verified_by_human"]:
        L += ["> WARNING: eval questions are drafted by an LLM and verified programmatically against the PDFs "
              "(gold passages exist verbatim at the stated page); they have NOT been reviewed by a human.", ""]
    L += metrics_table(s) + [""]
    L += ["## Per-question results", "", "| id | cat | split | status | gold rank | ms | faithful | correct |", "|---|---|---|---|---|---|---|---|"]
    for r in run["results"]:
        L.append(
            f"| {r['id']} | {r['category']} | {r['split']} | {r['status']} | {r['gold_rank'] or '-'} | "
            f"{r['timings_ms'].get('total', 0):.0f} | {r.get('faithful', '-')} | {r.get('correct', '-')} |"
        )
    return "\n".join(L) + "\n"


def write_compare(runs: dict[str, dict[str, Any]], title: str, extra_note: str = "") -> str:
    L = [f"# {title}", "", extra_note, ""]
    first = next(iter(runs.values()))["header"]
    L += [f"Timestamp {first['timestamp']}, commit `{first['git_commit']}`, answer model `{first['answer_model']}`.", ""]
    for split in ("test", "dev", "all"):
        L += [f"## Split: {split}", "",
              "| Mode | hit@1 | hit@5 | MRR@5 | Faithfulness | Correctness | Correct declines | Cost/question | p50 latency |",
              "|---|---|---|---|---|---|---|---|---|"]
        for mode, run in runs.items():
            s = run["summaries"][split]
            L.append(
                f"| {mode} | {pct(s.get('retrieval_hit@1'))} | {pct(s.get('retrieval_hit@5'))} | "
                f"{s.get('retrieval_mrr@5', 0):.3f} | {pct(s.get('faithfulness'))} | {pct(s.get('answer_correctness'))} | "
                f"{s.get('correct_declines', '-')}/{s.get('unanswerable_total', '-')} | {usd(s.get('cost_per_question_usd'))} | "
                f"{ms(s.get('latency_ms_p50'))} |"
            )
        L.append("")
    return "\n".join(L)
