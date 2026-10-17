"""Pydantic data models for CiteSure."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class Citation(BaseModel):
    chunk_id: str
    quote: str  # verbatim (whitespace-normalised) substring of chunk.text
    doc_id: str
    doc_title: str
    section_path: str
    page: int  # 1-based PDF page index containing the quote
    url: str  # "/docs/{doc_id}.pdf#page={page}"


class AnswerResponse(BaseModel):
    status: Literal["answered", "declined", "clarify"]
    answer: str | None = None
    citations: list[Citation] = Field(default_factory=list)
    clarifying_question: str | None = None
    checked_sections: list[str] = Field(default_factory=list)
    timings_ms: dict[str, float] = Field(default_factory=dict)
    usage: dict[str, int] = Field(default_factory=dict)
    cost_usd: float | None = None


class Chunk(BaseModel):
    chunk_id: str
    doc_id: str
    doc_title: str
    section_path: str
    page_start: int
    page_end: int
    kind: Literal["text", "table"] = "text"
    text: str
    context_text: str
    n_words: int
    # JSON-serialisable char_offset -> page map for multi-page chunks
    page_offsets: list[list[int]] = Field(default_factory=list)

    def page_for_offset(self, offset: int) -> int:
        """Resolve a character offset inside `text` to a 1-based PDF page."""
        if not self.page_offsets:
            return self.page_start
        page = self.page_start
        for start, pg in self.page_offsets:
            if offset >= start:
                page = pg
            else:
                break
        return page


class Passage(BaseModel):
    """A retrieved chunk ready for the answer prompt (labelled P1..Pn)."""

    label: str
    chunk: Chunk
    score: float = 0.0
    source_rank: dict[str, int] = Field(default_factory=dict)  # per-retriever ranks


class RetrievedChunk(BaseModel):
    chunk_id: str
    score: float
    rerank_score: float | None = None
    bm25_rank: int | None = None
    vector_rank: int | None = None
    rrf_rank: int | None = None


class Usage(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0
    cache_write_tokens: int = 0
    cache_read_tokens: int = 0

    def add(self, other: "Usage") -> "Usage":
        return Usage(
            input_tokens=self.input_tokens + other.input_tokens,
            output_tokens=self.output_tokens + other.output_tokens,
            cache_write_tokens=self.cache_write_tokens + other.cache_write_tokens,
            cache_read_tokens=self.cache_read_tokens + other.cache_read_tokens,
        )

    def as_dict(self) -> dict[str, int]:
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cache_write_tokens": self.cache_write_tokens,
            "cache_read_tokens": self.cache_read_tokens,
        }


class LLMResult(BaseModel):
    """Result of one LLM JSON completion."""

    data: dict[str, Any]
    usage: Usage = Field(default_factory=Usage)
    model: str = ""
    latency_ms: float = 0.0
