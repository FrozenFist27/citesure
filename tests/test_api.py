"""M8: API tests with a stubbed QA (no network, no models)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from citesure.app import create_app
from citesure.models import AnswerResponse, Citation
from citesure.ratelimit import RateLimiter


class StubQA:
    def __init__(self):
        self.calls = 0

    def ask(self, question, mode=None):
        self.calls += 1
        cite = Citation(chunk_id="d:1:001", quote="some verbatim words here", doc_id="csf-2.0",
                        doc_title="Doc", section_path="1", page=3, url="/docs/csf-2.0.pdf#page=3")
        return AnswerResponse(status="answered", answer="Claim. [1]", citations=[cite])


def _client(limiter=None):
    qa = StubQA()
    return TestClient(create_app(qa=qa, limiter=limiter)), qa


def test_ask_returns_schema_valid_response():
    c, qa = _client()
    r = c.post("/api/ask", json={"question": "What is a Profile in the CSF?"})
    assert r.status_code == 200
    body = AnswerResponse(**r.json())
    assert body.status == "answered" and body.citations[0].url.endswith("#page=3")
    assert qa.calls == 1


def test_empty_or_long_question_is_422():
    c, _ = _client()
    assert c.post("/api/ask", json={"question": ""}).status_code == 422
    assert c.post("/api/ask", json={"question": "x" * 501}).status_code == 422
    assert c.post("/api/ask", json={}).status_code == 422


def test_per_ip_rate_limit_429():
    c, _ = _client(RateLimiter(per_ip_per_hour=2, daily_cap=100))
    for _ in range(2):
        assert c.post("/api/ask", json={"question": "valid question"}).status_code == 200
    assert c.post("/api/ask", json={"question": "valid question"}).status_code == 429


def test_daily_cap_honoured():
    c, _ = _client(RateLimiter(per_ip_per_hour=100, daily_cap=1))
    assert c.post("/api/ask", json={"question": "valid question"}).status_code == 200
    r = c.post("/api/ask", json={"question": "another question"})
    assert r.status_code == 429 and "daily limit of 1 question" in r.json()["detail"]
    assert "cached" in r.json()["detail"]


def test_ip_limit_message_is_friendly_and_per_ip():
    c, _ = _client(RateLimiter(per_ip_per_hour=1, daily_cap=100))
    assert c.post("/api/ask", json={"question": "valid question"}).status_code == 200
    r = c.post("/api/ask", json={"question": "valid question"})
    assert r.status_code == 429 and "this hour" in r.json()["detail"]


def test_daily_cap_counts_only_live_questions():
    c, qa = _client(RateLimiter(per_ip_per_hour=100, daily_cap=100))
    for _ in range(3):
        c.post("/api/ask", json={"question": "valid question"})
    assert qa.calls == 3


def test_daily_cap_from_env_applies(monkeypatch):
    from citesure.config import reset_caches

    monkeypatch.setenv("DEMO_DAILY_QUESTION_CAP", "2")
    reset_caches()
    try:
        c, qa = _client()
        codes = [c.post("/api/ask", json={"question": "valid question"}).status_code for _ in range(3)]
        assert codes == [200, 200, 429] and qa.calls == 2
    finally:
        monkeypatch.delenv("DEMO_DAILY_QUESTION_CAP")
        reset_caches()


def test_rate_limiter_window_expires():
    t = [1000.0]
    lim = RateLimiter(1, 100, clock=lambda: t[0])
    assert lim.check("a") is None
    assert lim.check("a") == "ip"
    t[0] += 3601
    assert lim.check("a") is None


def test_health_index_and_pdf_404():
    c, _ = _client()
    assert c.get("/api/health").json()["status"] == "ok"
    assert "CiteSure" in c.get("/").text
    assert c.get("/docs/nope.pdf").status_code == 404
