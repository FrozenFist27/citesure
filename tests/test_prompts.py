"""Prompt construction and the relevance gate (no network, LLM mocked)."""

from __future__ import annotations

from citesure.llm.prompts import ANSWER_SYSTEM, answer_user_prompt, retry_user_prompt
from citesure.models import Chunk, LLMResult, Passage, RetrievedChunk, Usage
from citesure.qa import QA


def _passage(label="P1"):
    ch = Chunk(chunk_id="d:3:001", doc_id="d", doc_title="Doc Title", section_path="3 > Sec",
               page_start=3, page_end=3, text="Some passage text here.", context_text="x", n_words=4)
    return Passage(label=label, chunk=ch)


def test_system_prompt_has_schema_and_rules():
    assert "answer_sentences" in ANSWER_SYSTEM and "passage_id" in ANSWER_SYSTEM
    assert "declined" in ANSWER_SYSTEM and "clarify" in ANSWER_SYSTEM


def test_user_prompt_labels_passages_and_pages():
    u = answer_user_prompt("What?", [_passage("P1"), _passage("P2")])
    assert "[P1] Doc Title - 3 > Sec (page 3)" in u and "[P2]" in u and "Question: What?" in u


def test_retry_prompt_lists_bad_quotes():
    u = retry_user_prompt("What?", [_passage()], [("P1", "made up quote")])
    assert '- P1: "made up quote"' in u and "character for character" in u


class _Index:
    def __init__(self):
        self.chunks = {"d:3:001": _passage().chunk}


class _Retriever:
    index = _Index()

    def __init__(self, score):
        self.score = score

    def retrieve(self, q, mode):
        return [RetrievedChunk(chunk_id="d:3:001", score=self.score, rerank_score=self.score)], {"retrieve": 1.0, "rerank": 1.0}


class _Boom:
    model = "mock"
    called = False

    def complete_json(self, *a, **k):
        _Boom.called = True
        return LLMResult(data={"status": "declined"}, usage=Usage())


def test_gate_declines_without_calling_llm():
    qa = QA(retriever=_Retriever(-5.0), provider=_Boom())
    qa.settings.raw["retrieval"]["decline_threshold"] = 0.1
    qa.settings.raw["retrieval"]["gate_enabled"] = True
    resp = qa.ask("unrelated question", "hybrid_rerank")
    assert resp.status == "declined" and not _Boom.called and resp.checked_sections
    assert qa.last["gated"] is True


def test_gate_disabled_flag_lets_llm_decide():
    _Boom.called = False
    qa = QA(retriever=_Retriever(-5.0), provider=_Boom())
    qa.settings.raw["retrieval"]["decline_threshold"] = 0.1
    qa.settings.raw["retrieval"]["gate_enabled"] = False
    resp = qa.ask("unrelated question", "hybrid_rerank")
    assert _Boom.called and qa.last["gated"] is False
    assert resp.status == "declined"  # the answer model's own decline is still honoured
