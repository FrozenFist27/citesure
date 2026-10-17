"""M7: quote verification, gate and the generate/retry loop (LLM mocked, no network)."""

from __future__ import annotations

import pytest

from citesure.answer.gate import should_decline
from citesure.answer.generate import generate
from citesure.answer.verify import quote_page, verify_quote
from citesure.llm.base import LLMError, parse_json_loose
from citesure.models import Chunk, LLMResult, Passage, RetrievedChunk, Usage

TEXT = (
    "Verifiers shall require passwords that are used as a single-factor authentication\n"
    "mechanism to be at least 15 characters in length.\n\n"
    "Page two text: CSPs shall not impose composition rules on passwords."
)


def _chunk():
    return Chunk(chunk_id="d:1:001", doc_id="d", doc_title="Doc", section_path="3 > Passwords",
                 page_start=1, page_end=2, text=TEXT, context_text=TEXT, n_words=40,
                 page_offsets=[[0, 1], [TEXT.index("Page two"), 2]])


def _passages():
    return [Passage(label="P1", chunk=_chunk())]


class Scripted:
    model = "mock"

    def __init__(self, *outputs):
        self.outputs = list(outputs)
        self.calls = 0

    def complete_json(self, system, user, max_tokens=600):
        self.calls += 1
        o = self.outputs.pop(0)
        if isinstance(o, Exception):
            raise o
        return LLMResult(data=o, usage=Usage(input_tokens=100, output_tokens=20))


def _answer(quote):
    return {"status": "answered",
            "answer_sentences": [{"text": "Claim.", "citations": [{"passage_id": "P1", "quote": quote}]}]}


def test_exact_quote_passes_and_whitespace_normalised():
    c = _chunk()
    assert verify_quote(c, "passwords that are used as a single-factor authentication mechanism to be at least 15 characters")
    assert verify_quote(c, "passwords that are used as a single-factor authentication\nmechanism")


def test_paraphrase_fails():
    c = _chunk()
    assert not verify_quote(c, "passwords must have a minimum length of fifteen characters")
    assert not verify_quote(c, "")


def test_page_resolution_in_multi_page_chunk():
    c = _chunk()
    assert quote_page(c, "Verifiers shall require passwords that are used") == 1
    assert quote_page(c, "CSPs shall not impose composition rules on passwords") == 2


def test_gate():
    def r(s):
        return [RetrievedChunk(chunk_id="x", score=s, rerank_score=s)]

    assert should_decline(r(-5.0), 0.0)
    assert not should_decline(r(3.0), 0.0)
    assert should_decline([], 0.0)
    assert not should_decline([RetrievedChunk(chunk_id="x", score=0.1)], 0.0)  # no rerank score


def test_good_answer_verified():
    p = Scripted(_answer("Verifiers shall require passwords that are used as a single-factor"))
    g = generate(p, "q", _passages())
    assert g.status == "answered" and p.calls == 1
    assert g.sentences[0][1][0].url == "/docs/d.pdf#page=1"
    assert g.n_quotes == g.n_quotes_verified == 1


def test_bad_quote_triggers_retry_then_succeeds():
    p = Scripted(_answer("made up words that never appear anywhere"),
                 _answer("CSPs shall not impose composition rules on passwords"))
    g = generate(p, "q", _passages())
    assert p.calls == 2 and g.retried and g.status == "answered"
    assert g.sentences[0][1][0].page == 2
    assert g.usage.input_tokens == 200


def test_bad_quote_twice_declines():
    p = Scripted(_answer("totally invented quotation text"), _answer("another invented quotation here"))
    g = generate(p, "q", _passages())
    assert p.calls == 2 and g.status == "declined"


def test_unknown_passage_id_is_rejected():
    out = {"status": "answered", "answer_sentences": [
        {"text": "x", "citations": [{"passage_id": "P9", "quote": "Verifiers shall require passwords"}]}]}
    g = generate(Scripted(out, out), "q", _passages())
    assert g.status == "declined"


def test_llm_declines_and_clarifies():
    g = generate(Scripted({"status": "declined", "answer_sentences": []}), "q", _passages())
    assert g.status == "declined"
    g = generate(Scripted({"status": "clarify", "clarifying_question": "Which one?"}), "q", _passages())
    assert g.status == "clarify" and g.clarifying_question == "Which one?"


def test_invalid_json_retries_once_then_declines():
    p = Scripted(LLMError("bad"), LLMError("bad again"))
    g = generate(p, "q", _passages())
    assert p.calls == 2 and g.status == "declined"


def test_parse_json_loose():
    assert parse_json_loose('```json\n{"a": 1}\n```') == {"a": 1}
    assert parse_json_loose('Here: {"a": 2} done') == {"a": 2}
    with pytest.raises(LLMError):
        parse_json_loose("no json")
