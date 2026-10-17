"""LLM provider factory."""

from __future__ import annotations

from citesure.config import load_settings
from citesure.llm.base import LLMError, LLMProvider


def get_provider(model: str | None = None) -> LLMProvider:
    s = load_settings()
    model = model or s.answer_model
    if s.provider == "anthropic":
        from citesure.llm.anthropic_provider import AnthropicProvider

        return AnthropicProvider(model, temperature=float(s.answer.get("temperature", 0.0)))
    if s.provider == "gemini":
        from citesure.llm.gemini_provider import GeminiProvider

        return GeminiProvider(model)
    raise LLMError(f"unknown LLM_PROVIDER {s.provider!r}")
