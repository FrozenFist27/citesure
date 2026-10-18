"""FastAPI app: GET / (chat page), POST /api/ask, GET /api/health, GET /docs/{doc}.pdf."""

from __future__ import annotations

import json
import os
import threading
from pathlib import Path

import yaml
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from citesure.config import PROJECT_ROOT, load_settings
from citesure.models import AnswerResponse
from citesure.qa import QA
from citesure.ratelimit import RateLimiter

STATIC_DIR = PROJECT_ROOT / "static"
EXAMPLES_PATH = PROJECT_ROOT / "static" / "examples.json"


class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=500)


def create_app(qa: QA | None = None, limiter: RateLimiter | None = None) -> FastAPI:
    settings = load_settings()
    app = FastAPI(title="CiteSure", version="0.1.0")
    state = {"qa": qa}
    lim = limiter or RateLimiter(
        int(settings.limits.get("rate_limit_per_ip_per_hour", 10)),
        int(settings.limits.get("daily_question_cap", 100)),
    )
    manifest = yaml.safe_load(settings.manifest_path.read_text(encoding="utf-8"))
    pdfs = {d["doc_id"]: d["filename"] for d in manifest["documents"]}

    def get_qa() -> QA:
        if state["qa"] is None:
            state["qa"] = QA()
        return state["qa"]

    def _warmup() -> None:
        """Load index + embedding/re-rank models in the background so the first question is fast."""
        try:
            q = get_qa()
            q.retriever.retrieve("warmup", settings.retrieval.get("mode", "hybrid_rerank"))
        except Exception:  # noqa: BLE001 - warmup is best-effort
            pass

    if qa is None and os.environ.get("CITESURE_WARMUP") == "1":
        threading.Thread(target=_warmup, daemon=True).start()

    cache: dict[str, AnswerResponse] = {}
    if EXAMPLES_PATH.exists():
        for ex in json.loads(EXAMPLES_PATH.read_text(encoding="utf-8")).get("cached", []):
            cache[ex["question"].strip().lower()] = AnswerResponse(**ex["response"])

    @app.get("/api/health")
    def health():
        return {"status": "ok", "model": settings.answer_model, "mode": settings.retrieval.get("mode")}

    @app.get("/api/examples")
    def examples():
        if EXAMPLES_PATH.exists():
            return [e["question"] for e in json.loads(EXAMPLES_PATH.read_text(encoding="utf-8")).get("cached", [])]
        return []

    @app.post("/api/ask", response_model=AnswerResponse)
    def ask(req: AskRequest, request: Request):
        q = req.question.strip()
        if len(q) < 3:
            raise HTTPException(status_code=422, detail="question too short")
        hit = cache.get(q.lower())
        if hit is not None:
            return hit
        ip = request.client.host if request.client else "unknown"
        reason = lim.check(ip)
        if reason == "daily":
            return JSONResponse(
                status_code=429,
                content={
                    "detail": (
                        f"The demo has reached its daily limit of {lim.daily_cap} questions to keep "
                        "costs down. The example questions above still work (cached), and the "
                        "limit resets at 00:00 UTC. You can also run CiteSure locally."
                    )
                },
            )
        if reason == "ip":
            return JSONResponse(status_code=429, content={
                    "detail": (
                        f"You have used your {lim.per_ip} live questions for this hour. Try the "
                        "cached example questions or come back a bit later."
                    )
                },
            )
        return get_qa().ask(q)

    @app.get("/docs/{doc_id}.pdf")
    def pdf(doc_id: str):
        fn = pdfs.get(doc_id)
        path = settings.docs_dir / fn if fn else None
        if not path or not Path(path).exists():
            raise HTTPException(status_code=404, detail="unknown document")
        return FileResponse(path, media_type="application/pdf", headers={"Content-Disposition": "inline"})

    @app.get("/")
    def index():
        return FileResponse(STATIC_DIR / "index.html")

    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    return app


app = create_app()
