"""LLM judge (eval only): faithfulness and correctness, temperature 0, JSON output."""

from __future__ import annotations

from citesure.config import pricing_for
from citesure.llm.base import LLMError
from citesure.llm.prompts import JUDGE_CORRECT_SYSTEM, JUDGE_FAITHFUL_SYSTEM
from citesure.models import AnswerResponse, Chunk


class Judge:
    def __init__(self, provider, model: str):
        self.provider = provider
        self.model = model
        self.cost_usd = 0.0

    def _call(self, system: str, user: str) -> dict | None:
        for _ in range(2):
            try:
                res = self.provider.complete_json(system, user, max_tokens=250)
            except LLMError:
                continue
            u = res.usage
            c = pricing_for(self.model).cost_usd(
                u.input_tokens, u.output_tokens, u.cache_write_tokens, u.cache_read_tokens
            )
            self.last_cost = c or 0.0
            self.cost_usd += self.last_cost
            return res.data
        self.last_cost = 0.0
        return None

    def faithfulness(self, resp: AnswerResponse, chunks: dict[str, Chunk]) -> tuple[int | None, str]:
        seen, parts = set(), []
        for c in resp.citations:
            if c.chunk_id in seen or c.chunk_id not in chunks:
                continue
            seen.add(c.chunk_id)
            parts.append(f"[{c.doc_title}, page {c.page}]\n{chunks[c.chunk_id].text}")
        user = (
            "QUOTED PASSAGES:\n\n" + "\n\n".join(parts) + f"\n\nANSWER:\n{resp.answer}\n\nReturn the JSON now."
        )
        d = self._call(JUDGE_FAITHFUL_SYSTEM, user)
        if not d or "supported" not in d:
            return None, "judge_error"
        return int(bool(int(d["supported"]))), str(d.get("reason", ""))

    def correctness(self, question: str, gold: str, resp: AnswerResponse) -> tuple[int | None, str]:
        user = f"QUESTION: {question}\n\nGOLD: {gold}\n\nSYSTEM ANSWER: {resp.answer}\n\nReturn the JSON now."
        d = self._call(JUDGE_CORRECT_SYSTEM, user)
        if not d or "correct" not in d:
            return None, "judge_error"
        return int(bool(int(d["correct"]))), str(d.get("reason", ""))
