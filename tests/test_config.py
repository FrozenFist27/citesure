"""M0 smoke tests: config loads, models validate, pricing present."""

from __future__ import annotations

from citesure.config import load_settings, pricing_for
from citesure.models import AnswerResponse, Citation, Usage


def test_settings_loads_defaults():
    s = load_settings()
    assert s.provider in {"anthropic", "gemini"}
    assert s.answer_model
    assert s.retrieval["mode"] in {"vector", "bm25", "hybrid", "hybrid_rerank"}
    assert s.limits["daily_question_cap"] >= 1


def test_pricing_known_for_default_model():
    s = load_settings()
    p = pricing_for(s.answer_model)
    assert p.known, "default answer model must have prices in pricing.yaml"
    # $0.10 input / $0.50 output per MTok for claude-haiku-5-5 (<=100K prompt tier)
    assert p.cost_usd(1_000_000, 1_000_000) == 0.6


def test_pricing_unknown_model_is_null():
    p = pricing_for("some-unknown-model")
    assert not p.known
    assert p.cost_usd(1000, 1000) is None


def test_answer_response_schema():
    r = AnswerResponse(
        status="answered",
        answer="Yes. [1]",
        citations=[
            Citation(
                chunk_id="csf:3:001",
                quote="exactly this text",
                doc_id="csf",
                doc_title="NIST CSF 2.0",
                section_path="1 > 1.1",
                page=3,
                url="/docs/csf.pdf#page=3",
            )
        ],
        timings_ms={"total": 12.5},
        usage={"input_tokens": 10, "output_tokens": 5},
        cost_usd=0.0001,
    )
    assert r.status == "answered"
    assert r.citations[0].page == 3


def test_usage_add():
    a = Usage(input_tokens=10, output_tokens=5, cache_read_tokens=100)
    b = Usage(input_tokens=3, output_tokens=2, cache_write_tokens=50)
    c = a.add(b)
    assert (c.input_tokens, c.output_tokens, c.cache_read_tokens, c.cache_write_tokens) == (
        13,
        7,
        100,
        50,
    )


def test_daily_cap_default_and_env_override(monkeypatch):
    from citesure.config import reset_caches

    monkeypatch.setattr("citesure.config.load_dotenv", lambda *a, **k: None)  # ignore a local .env
    for var in ("DEMO_DAILY_QUESTION_CAP", "DAILY_QUESTION_CAP"):
        monkeypatch.delenv(var, raising=False)
    reset_caches()
    assert load_settings().limits["daily_question_cap"] == 100
    monkeypatch.setenv("DEMO_DAILY_QUESTION_CAP", "2")
    reset_caches()
    assert load_settings().limits["daily_question_cap"] == 2
    monkeypatch.delenv("DEMO_DAILY_QUESTION_CAP")
    monkeypatch.setenv("DAILY_QUESTION_CAP", "7")
    reset_caches()
    assert load_settings().limits["daily_question_cap"] == 7
    reset_caches()
