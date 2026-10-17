"""Provider interface: complete_json(system, user, max_tokens) -> LLMResult."""

from __future__ import annotations

import json
import re
from typing import Protocol

from citesure.models import LLMResult


class LLMError(RuntimeError):
    pass


class LLMProvider(Protocol):
    model: str

    def complete_json(self, system: str, user: str, max_tokens: int = 600) -> LLMResult: ...


_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE)


def parse_json_loose(text: str) -> dict:
    """Parse a JSON object from model output, tolerating code fences and prose."""
    t = _FENCE.sub("", text.strip()).strip()
    try:
        obj = json.loads(t)
    except json.JSONDecodeError:
        start, end = t.find("{"), t.rfind("}")
        if start < 0 or end <= start:
            raise LLMError("no JSON object in model output")
        try:
            obj = json.loads(t[start : end + 1])
        except json.JSONDecodeError as e:
            raise LLMError(f"invalid JSON in model output: {e}") from e
    if not isinstance(obj, dict):
        raise LLMError("model output JSON is not an object")
    return obj
