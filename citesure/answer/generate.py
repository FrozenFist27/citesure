"""Answer generation: LLM call + deterministic verification + one retry."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from citesure.answer.verify import quote_page, verify_quote
from citesure.llm.base import LLMError, LLMProvider
from citesure.llm.prompts import ANSWER_SYSTEM, answer_user_prompt, retry_user_prompt
from citesure.models import Citation, Passage, Usage


@dataclass
class Generated:
    status: str  # answered | declined | clarify
    sentences: list[tuple[str, list[Citation]]] = field(default_factory=list)
    clarifying_question: str | None = None
    usage: Usage = field(default_factory=Usage)
    llm_ms: float = 0.0
    verify_ms: float = 0.0
    retried: bool = False
    n_quotes: int = 0
    n_quotes_verified: int = 0
    note: str = ""


def _check(data: dict[str, Any], by_label: dict[str, Passage]):
    """Return (good_sentences, bad_quotes, n_quotes, n_verified)."""
    good: list[tuple[str, list[Citation]]] = []
    bad: list[tuple[str, str]] = []
    n_q = n_ok = 0
    sentences = data.get("answer_sentences") or []
    if not isinstance(sentences, list):
        sentences = []
    for s in sentences:
        if not isinstance(s, dict):
            continue
        text = str(s.get("text", "")).strip()
        cites: list[Citation] = []
        for c in s.get("citations") or []:
            if not isinstance(c, dict):
                continue
            pid, quote = str(c.get("passage_id", "")).strip(), str(c.get("quote", "")).strip()
            n_q += 1
            p = by_label.get(pid)
            if p is None or not verify_quote(p.chunk, quote):
                bad.append((pid, quote))
                continue
            n_ok += 1
            ch = p.chunk
            page = quote_page(ch, quote)
            cites.append(
                Citation(
                    chunk_id=ch.chunk_id,
                    quote=quote,
                    doc_id=ch.doc_id,
                    doc_title=ch.doc_title,
                    section_path=ch.section_path,
                    page=page,
                    url=f"/docs/{ch.doc_id}.pdf#page={page}",
                )
            )
        if text and cites:
            good.append((text, cites))
        elif text:
            bad.append(("", text[:80]))
    return good, bad, n_q, n_ok


def generate(
    provider: LLMProvider,
    question: str,
    passages: list[Passage],
    max_tokens: int = 600,
    retries: int = 1,
) -> Generated:
    by_label = {p.label: p for p in passages}
    gen = Generated(status="declined")
    user = answer_user_prompt(question, passages)
    import time

    attempt = 0
    while True:
        t0 = time.perf_counter()
        try:
            res = provider.complete_json(ANSWER_SYSTEM, user, max_tokens=max_tokens)
        except LLMError as e:
            gen.llm_ms += (time.perf_counter() - t0) * 1000
            if attempt < retries:
                attempt += 1
                gen.retried = True
                continue
            gen.note = f"llm_error: {e}"
            return gen
        gen.llm_ms += (time.perf_counter() - t0) * 1000
        gen.usage = gen.usage.add(res.usage)

        data = res.data
        status = str(data.get("status", "")).lower()
        if status == "clarify" and data.get("clarifying_question"):
            gen.status = "clarify"
            gen.clarifying_question = str(data["clarifying_question"]).strip()
            return gen
        if status == "declined":
            gen.status = "declined"
            return gen

        t1 = time.perf_counter()
        good, bad, n_q, n_ok = _check(data, by_label)
        gen.verify_ms += (time.perf_counter() - t1) * 1000
        gen.n_quotes += n_q
        gen.n_quotes_verified += n_ok
        if good and not bad:
            gen.status, gen.sentences = "answered", good
            return gen
        if attempt < retries:
            attempt += 1
            gen.retried = True
            user = retry_user_prompt(question, passages, bad or [("", "(no valid citations)")])
            continue
        if good:  # keep only the sentences whose quotes verified
            gen.status, gen.sentences = "answered", good
            gen.note = "dropped_unverified_sentences"
        else:
            gen.status, gen.note = "declined", "no_verifiable_citations"
        return gen
