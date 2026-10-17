# CiteSure

**Answers from your documents — with the exact quote and page, or an honest "I don't know".**

> Demo project built on public NIST documents. Not client work.

[[PLACEHOLDER — results table filled from a real `make eval` run.]]

## Status

Scaffold (milestone M0). Build follows IDEATION.md milestones M0–M13.

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
python scripts/make_env.py      # creates .env from the workspace secrets file
python scripts/download_corpus.py
python -m citesure.ingest.cli all
python -m uvicorn citesure.app:app --port 8000
python -m pytest
```

(Full sections — problem, approach, architecture, results, cost, limitations — are
written in M13 once measured numbers exist.)
