"""Anthropic provider (claude-haiku-5-5 by default) with prompt caching on the system prompt.

The installed SDK/model exposes no `temperature` parameter, so the model default is used."""

from __future__ import annotations

import os
import time

from citesure.llm.base import LLMError, parse_json_loose
from citesure.models import LLMResult, Usage


class AnthropicProvider:
    def __init__(self, model: str, api_key: str | None = None, temperature: float = 0.0):
        import anthropic

        key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            raise LLMError("ANTHROPIC_API_KEY is not set")
        # Always talk to the real Anthropic API unless CITESURE_ANTHROPIC_BASE_URL says otherwise; an ambient
        # ANTHROPIC_BASE_URL (e.g. set by a dev tool or proxy) must not silently redirect this app's key.
        base_url = os.environ.get("CITESURE_ANTHROPIC_BASE_URL", "https://api.anthropic.com")
        self.client = anthropic.Anthropic(api_key=key, base_url=base_url, max_retries=3, timeout=60.0)
        self.model = model
        self.temperature = temperature

    def complete_json(self, system: str, user: str, max_tokens: int = 600) -> LLMResult:
        t0 = time.perf_counter()
        resp = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            thinking={"type": "disabled"},
            system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
            messages=[{"role": "user", "content": user}],
        )
        latency = (time.perf_counter() - t0) * 1000
        text = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
        u = resp.usage
        usage = Usage(
            input_tokens=getattr(u, "input_tokens", 0) or 0,
            output_tokens=getattr(u, "output_tokens", 0) or 0,
            cache_write_tokens=getattr(u, "cache_creation_input_tokens", 0) or 0,
            cache_read_tokens=getattr(u, "cache_read_input_tokens", 0) or 0,
        )
        data = parse_json_loose(text)
        return LLMResult(data=data, usage=usage, model=self.model, latency_ms=latency)
