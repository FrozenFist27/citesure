"""Single entry point: ask(question, mode) -> AnswerResponse."""

from __future__ import annotations

import time

from citesure.answer.gate import should_decline
from citesure.answer.generate import generate
from citesure.config import load_settings, pricing_for
from citesure.models import AnswerResponse, Passage, Usage
from citesure.retrieval.pipeline import Retriever


class QA:
    def __init__(self, retriever: Retriever | None = None, provider=None, settings=None):
        self.settings = settings or load_settings()
        self._retriever = retriever
        self._provider = provider
        self.last: dict = {}  # diagnostics of the most recent ask(): retrieved chunks, gate flag

    @property
    def retriever(self) -> Retriever:
        if self._retriever is None:
            self._retriever = Retriever(settings=self.settings)
        return self._retriever

    @property
    def provider(self):
        if self._provider is None:
            from citesure.llm import get_provider

            self._provider = get_provider()
        return self._provider

    def ask(self, question: str, mode: str | None = None) -> AnswerResponse:
        t_all = time.perf_counter()
        s = self.settings
        mode = mode or s.retrieval.get("mode", "hybrid_rerank")
        retrieved, timings = self.retriever.retrieve(question, mode)
        index = self.retriever.index
        checked = [
            f"{index.chunks[r.chunk_id].doc_title} - {index.chunks[r.chunk_id].section_path} "
            f"(p. {index.chunks[r.chunk_id].page_start})"
            for r in retrieved[:3]
        ]
        timings = dict(timings)
        self.last = {"retrieved": retrieved, "gated": False}

        def finish(resp: AnswerResponse) -> AnswerResponse:
            timings.setdefault("llm", 0.0)
            timings.setdefault("verify", 0.0)
            timings["total"] = (time.perf_counter() - t_all) * 1000
            resp.timings_ms = {k: round(v, 1) for k, v in timings.items()}
            return resp

        threshold = float(s.retrieval.get("decline_threshold", 0.0))
        if mode == "hybrid_rerank" and should_decline(retrieved, threshold):
            self.last["gated"] = True
            return finish(AnswerResponse(status="declined", checked_sections=checked,
                                         answer="I don't know - the documents don't cover this."))

        passages = [
            Passage(label=f"P{i}", chunk=index.chunks[r.chunk_id], score=r.score)
            for i, r in enumerate(retrieved[: int(s.answer.get("max_passages", 5))], 1)
        ]
        gen = generate(
            self.provider,
            question,
            passages,
            max_tokens=int(s.answer.get("max_tokens", 600)),
            retries=int(s.answer.get("retry_on_verify_fail", 1)),
        )
        timings["llm"] = gen.llm_ms
        timings["verify"] = gen.verify_ms
        usage: Usage = gen.usage
        cost = pricing_for(s.answer_model).cost_usd(
            usage.input_tokens, usage.output_tokens, usage.cache_write_tokens, usage.cache_read_tokens
        )
        base = dict(usage=usage.as_dict(), cost_usd=cost)

        if gen.status == "clarify":
            return finish(AnswerResponse(status="clarify", clarifying_question=gen.clarifying_question,
                                         checked_sections=checked, **base))
        if gen.status != "answered":
            return finish(AnswerResponse(status="declined", checked_sections=checked,
                                         answer="I don't know - the documents don't cover this.", **base))

        # build answer text with [n] markers; number unique (chunk, quote) citations
        cards, numbers = [], {}
        parts = []
        for text, cites in gen.sentences:
            marks = ""
            for c in cites:
                key = (c.chunk_id, c.quote)
                if key not in numbers:
                    cards.append(c)
                    numbers[key] = len(cards)
                marks += f"[{numbers[key]}]"
            parts.append(f"{text} {marks}")
        return finish(AnswerResponse(status="answered", answer=" ".join(parts), citations=cards,
                                     checked_sections=checked, **base))
