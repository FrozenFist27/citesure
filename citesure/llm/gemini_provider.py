"""Optional Gemini adapter (install extra: pip install -e .[gemini]). Not used by default."""

from __future__ import annotations

import os
import time

from citesure.llm.base import LLMError, parse_json_loose
from citesure.models import LLMResult, Usage


class GeminiProvider:  # pragma: no cover - optional, untested against the live API
    def __init__(self, model: str, api_key: str | None = None):
        try:
            from google import genai
        except ImportError as e:
            raise LLMError("google-genai not installed; pip install -e .[gemini]") from e
        key = api_key or os.environ.get("GEMINI_API_KEY")
        if not key:
            raise LLMError("GEMINI_API_KEY is not set")
        self.client = genai.Client(api_key=key)
        self.model = model

    def complete_json(self, system: str, user: str, max_tokens: int = 600) -> LLMResult:
        from google.genai import types

        t0 = time.perf_counter()
        resp = self.client.models.generate_content(
            model=self.model,
            contents=user,
            config=types.GenerateContentConfig(
                system_instruction=system,
                max_output_tokens=max_tokens,
                temperature=0.0,
                response_mime_type="application/json",
            ),
        )
        um = resp.usage_metadata
        usage = Usage(
            input_tokens=getattr(um, "prompt_token_count", 0) or 0,
            output_tokens=getattr(um, "candidates_token_count", 0) or 0,
        )
        return LLMResult(
            data=parse_json_loose(resp.text or ""),
            usage=usage,
            model=self.model,
            latency_ms=(time.perf_counter() - t0) * 1000,
        )
