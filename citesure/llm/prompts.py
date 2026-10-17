"""Prompts for answer generation, retry and eval judging."""

from __future__ import annotations

from citesure.models import Passage

ANSWER_SYSTEM = """You answer questions using ONLY the numbered passages provided by the user. You have no other knowledge.

Rules:
1. Every sentence of your answer must cite at least one passage and include a quote copied character-for-character from that passage (8 to 40 words, no ellipses, no paraphrasing inside the quote).
2. If the passages do not contain the answer, return status "declined" with an empty answer_sentences list. Do not guess. If the passages cover only part of the question, answer only the covered part and say what is not covered.
3. If the question is ambiguous between distinct meanings that appear in the passages, return status "clarify" with one short clarifying_question and an empty answer_sentences list.
4. Keep the answer to at most 4 sentences. Neutral tone. Do not add advice beyond what the text says.
5. Output ONLY a JSON object, no prose, no code fences, matching this schema:
{
  "status": "answered" | "declined" | "clarify",
  "answer_sentences": [
    {"text": "short claim sentence", "citations": [{"passage_id": "P2", "quote": "exact words copied from P2"}]}
  ],
  "clarifying_question": null
}"""


def format_passages(passages: list[Passage]) -> str:
    blocks = []
    for p in passages:
        c = p.chunk
        blocks.append(f"[{p.label}] {c.doc_title} - {c.section_path} (page {c.page_start})\n{c.text}")
    return "\n\n".join(blocks)


def answer_user_prompt(question: str, passages: list[Passage]) -> str:
    return (
        f"Passages:\n\n{format_passages(passages)}\n\nQuestion: {question}\n\n"
        "Return the JSON object now."
    )


def retry_user_prompt(question: str, passages: list[Passage], bad: list[tuple[str, str]]) -> str:
    lines = "\n".join(f'- {pid}: "{q}"' for pid, q in bad)
    return (
        answer_user_prompt(question, passages)
        + "\n\nThese quotes were not found verbatim in the cited passage:\n"
        + lines
        + "\nCopy quotes exactly from the passage text, character for character, or decline."
    )


JUDGE_FAITHFUL_SYSTEM = (
    "You are a strict grader. Given an ANSWER and the QUOTED PASSAGES it cites, decide whether "
    "every claim in the answer is directly supported by those quoted passages (no outside "
    'knowledge). Output ONLY JSON: {"supported": 0 or 1, "unsupported_claims": [..], '
    '"reason": "one sentence"}'
)

JUDGE_CORRECT_SYSTEM = (
    "You are a strict grader. Given a QUESTION, a GOLD answer and a SYSTEM answer, decide whether "
    "the system answer conveys the gold answer's key facts without contradicting them. Extra "
    'correct detail is fine. Output ONLY JSON: {"correct": 0 or 1, "reason": "one sentence"}'
)
