"""Load configuration from config/*.yaml plus environment (.env).

Model ids and the provider come from the environment (LLM_PROVIDER, LLM_MODEL,
JUDGE_MODEL) so they can be swapped without code changes.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = PROJECT_ROOT / "config"


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


@dataclass
class Pricing:
    """Per-1M-token USD prices for one model; None means "unknown"."""

    input_per_mtok: float | None = None
    output_per_mtok: float | None = None
    cache_write_per_mtok: float | None = None
    cache_read_per_mtok: float | None = None

    @classmethod
    def from_dict(cls, d: dict[str, Any] | None) -> "Pricing":
        d = d or {}
        return cls(
            input_per_mtok=d.get("input_per_mtok"),
            output_per_mtok=d.get("output_per_mtok"),
            cache_write_per_mtok=d.get("cache_write_per_mtok"),
            cache_read_per_mtok=d.get("cache_read_per_mtok"),
        )

    @property
    def known(self) -> bool:
        return self.input_per_mtok is not None and self.output_per_mtok is not None

    def cost_usd(
        self,
        input_tokens: int,
        output_tokens: int,
        cache_write_tokens: int = 0,
        cache_read_tokens: int = 0,
    ) -> float | None:
        if not self.known:
            return None
        assert self.input_per_mtok is not None and self.output_per_mtok is not None
        cost = (
            input_tokens * self.input_per_mtok
            + output_tokens * self.output_per_mtok
            + cache_write_tokens * (self.cache_write_per_mtok or self.input_per_mtok)
            + cache_read_tokens * (self.cache_read_per_mtok or 0.0)
        ) / 1_000_000
        return round(cost, 8)


@dataclass
class Settings:
    raw: dict[str, Any] = field(default_factory=dict)

    # env
    provider: str = "anthropic"
    answer_model: str = "claude-haiku-5-5"
    judge_model: str = "claude-haiku-5-5"

    @property
    def retrieval(self) -> dict[str, Any]:
        return self.raw.get("retrieval", {})

    @property
    def chunking(self) -> dict[str, Any]:
        return self.raw.get("chunking", {})

    @property
    def embeddings(self) -> dict[str, Any]:
        return self.raw.get("embeddings", {})

    @property
    def reranker(self) -> dict[str, Any]:
        return self.raw.get("reranker", {})

    @property
    def answer(self) -> dict[str, Any]:
        return self.raw.get("answer", {})

    @property
    def limits(self) -> dict[str, Any]:
        return self.raw.get("limits", {})

    @property
    def paths(self) -> dict[str, Any]:
        return self.raw.get("paths", {})

    @property
    def data_dir(self) -> Path:
        return PROJECT_ROOT / self.paths.get("data_dir", "data")

    @property
    def index_dir(self) -> Path:
        return PROJECT_ROOT / self.paths.get("index_dir", "index")

    @property
    def reports_dir(self) -> Path:
        return PROJECT_ROOT / self.paths.get("reports_dir", "reports")

    @property
    def docs_dir(self) -> Path:
        return PROJECT_ROOT / self.paths.get("docs_dir", "data/raw")

    @property
    def manifest_path(self) -> Path:
        return self.data_dir / "corpus_manifest.yaml"


def _pricing_table() -> dict[str, Any]:
    return _load_yaml(CONFIG_DIR / "pricing.yaml")


@lru_cache(maxsize=1)
def load_settings() -> Settings:
    """Load settings.yaml + .env. Cached for the process lifetime."""
    load_dotenv(PROJECT_ROOT / ".env", override=False)
    raw = _load_yaml(CONFIG_DIR / "settings.yaml")

    provider = os.environ.get("LLM_PROVIDER", "anthropic").strip().lower()
    answer_model = os.environ.get("LLM_MODEL", "claude-haiku-5-5").strip()
    judge_model = os.environ.get("JUDGE_MODEL", answer_model).strip()

    # env overrides for limits
    limits = dict(raw.get("limits", {}))
    if os.environ.get("DAILY_QUESTION_CAP"):
        limits["daily_question_cap"] = int(os.environ["DAILY_QUESTION_CAP"])
    if os.environ.get("RATE_LIMIT_PER_IP_PER_HOUR"):
        limits["rate_limit_per_ip_per_hour"] = int(os.environ["RATE_LIMIT_PER_IP_PER_HOUR"])
    raw["limits"] = limits

    return Settings(raw=raw, provider=provider, answer_model=answer_model, judge_model=judge_model)


def pricing_for(model_id: str) -> Pricing:
    """Look up pricing.yaml for a model id; falls back to the null default block."""
    table = _pricing_table()
    models = table.get("models", {})
    entry = models.get(model_id) or table.get("default") or {}
    return Pricing.from_dict(entry)


def reset_caches() -> None:
    """Testing helper: clear cached settings."""
    load_settings.cache_clear()
