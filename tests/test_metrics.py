"""M10: metric computations on hand-made results."""

from __future__ import annotations

from citesure.eval import metrics as M
from citesure.eval.report import write_compare
from citesure.models import Chunk


def _ch(doc, p0, p1, text):
    return Chunk(chunk_id=f"{doc}:{p0}", doc_id=doc, doc_title=doc, section_path="s", page_start=p0,
                 page_end=p1, text=text, context_text=text, n_words=len(text.split()))


GOLD = {"doc_id": "a", "page": 5, "passage": "passwords shall be at least fifteen characters long"}


def test_chunk_matches_gold_exact_and_fuzzy():
    assert M.chunk_matches_gold(_ch("a", 5, 5, "x Passwords SHALL be at least fifteen characters long y"), GOLD)
    # wrong doc / wrong page
    assert not M.chunk_matches_gold(_ch("b", 5, 5, GOLD["passage"]), GOLD)
    assert not M.chunk_matches_gold(_ch("a", 6, 7, GOLD["passage"]), GOLD)
    # fuzzy: most trigrams present
    assert M.chunk_matches_gold(_ch("a", 4, 6, "passwords shall be at least fifteen characters in total"), GOLD)
    assert not M.chunk_matches_gold(_ch("a", 5, 5, "completely unrelated text about incidents"), GOLD)


def test_rank_and_require_all():
    other = _ch("a", 9, 9, "nothing here")
    hit = _ch("a", 5, 5, GOLD["passage"])
    assert M.first_gold_rank([other, hit], [GOLD]) == 2
    assert M.first_gold_rank([other], [GOLD]) is None
    g2 = {"doc_id": "a", "page": 9, "passage": "nothing here"}
    assert M.first_gold_rank([other, hit], [GOLD, g2], require_all=True) == 2
    assert M.first_gold_rank([hit], [GOLD, g2], require_all=True) is None
    assert M.first_gold_rank([hit], [GOLD, g2], require_all=False) == 1


def test_retrieval_metrics():
    m = M.retrieval_metrics([1, 2, None, 6, 5])
    assert m["n"] == 5
    assert m["hit@1"] == 0.2
    assert m["hit@5"] == 0.6  # ranks 1, 2, 5
    assert abs(m["mrr@5"] - (1 + 0.5 + 0.2) / 5) < 1e-9


def _r(**kw):
    base = {"answerable": True, "status": "answered", "gold_rank": 1, "timings_ms": {"total": 100.0},
            "n_citations": 1, "n_citations_verified": 1, "cited_gold_page": True,
            "faithful": 1, "correct": 1, "cost_usd": 0.001}
    base.update(kw)
    return base


def test_summarize_declines_faithfulness_cost_latency():
    results = [
        _r(),
        _r(gold_rank=None, faithful=0, correct=0, timings_ms={"total": 300.0}, cost_usd=0.003),
        _r(answerable=True, status="declined", gold_rank=None, faithful=None, correct=0,
           n_citations=0, n_citations_verified=0, cited_gold_page=False),
        _r(answerable=False, status="declined", gold_rank=None, faithful=None, correct=None,
           n_citations=0, n_citations_verified=0, cited_gold_page=False),
        _r(answerable=False, status="answered", gold_rank=None, faithful=0, correct=None),
    ]
    s = M.summarize(results)
    assert s["n_answerable"] == 3 and s["n_unanswerable"] == 2
    assert s["correct_declines"] == 1 and s["unanswerable_total"] == 2
    assert abs(s["false_decline_rate"] - 1 / 3) < 1e-9
    assert abs(s["faithfulness"] - 1 / 3) < 1e-9 and s["n_faithfulness_judged"] == 3
    assert s["quote_verification_rate"] == 1.0
    assert s["latency_ms_p50"] == 100.0
    assert abs(s["cost_per_question_usd"] - (0.001 + 0.003 + 0.001 + 0.001 + 0.001) / 5) < 1e-9
    assert abs(s["retrieval_hit@1"] - 1 / 3) < 1e-9


def test_compare_report_renders():
    s = M.summarize([_r()])
    run = {"header": {"timestamp": "t", "git_commit": "c", "answer_model": "m"},
           "summaries": {"test": s, "dev": s, "all": s}}
    md = write_compare({"vector": run}, "T")
    assert "| vector |" in md and "100.0%" in md
