# CiteSure

**Answers from your documents, with the exact quote and page, or an honest "I don't know".**

> Demo project built on public NIST documents. Not client work.
> Live demo: not deployed (no Hugging Face token was available; the repo is Space-ready, see `Dockerfile`).
> Video: script in `docs/VIDEO_SCRIPT.md` (to be recorded).

## Problem

Document chatbots sound confident when they are wrong. For compliance, HR and support teams a wrong answer costs
trust, and nobody can check an answer without hunting through hundreds of pages. Most teams also never measure how
often the bot is right.

## Approach

- Section-aware PDF parsing (pdfplumber): headings, page numbers, tables as Markdown, running headers removed.
- Hybrid retrieval: BM25 + `BAAI/bge-small-en-v1.5` embeddings fused with Reciprocal Rank Fusion, then a local
  cross-encoder re-rank (`ms-marco-MiniLM-L-6-v2`).
- Answers only from the top passages. The LLM (`claude-haiku-5-5`) must return JSON with a verbatim quote per sentence.
- Deterministic verification: each quote must be an exact (whitespace-normalised) substring of the cited chunk,
  otherwise it is dropped, the model gets one retry, and if nothing verifies the answer is a decline. Every citation
  shows the quote, section and a link that opens the PDF at the quoted page.
- Relevance gate: if the best re-rank score is below a threshold calibrated on a dev split, CiteSure declines without
  calling the LLM (saves cost). Declines list the closest sections it checked. Ambiguous questions get a clarifying question.
- One-command evaluation report and a before/after comparison.

Corpus (329 pages, public US-government works): NIST CSF 2.0, SP 800-61r3, SP 800-171r3, SP 800-63B-4
(886 chunks, 153 of them tables).

## Architecture

```
 data/raw/*.pdf -> parse.py -> chunk.py -> index/ (SQLite chunks, BM25 pickle, embeddings .npy)

 question -> BM25 top20 + vector top20 -> RRF -> cross-encoder re-rank -> top5
          -> gate (best score < threshold: DECLINE, no LLM call)
          -> LLM JSON answer (quote per sentence) -> verify quotes (exact substring) -> retry once -> answer | decline
 FastAPI: GET / (chat page), POST /api/ask, GET /docs/{doc}.pdf#page=N, GET /api/health
 eval:    python -m citesure.eval.run  ->  reports/eval_<ts>.{md,json}
```

## Results (real run, 2026-10-17, commit `badad54`, model `claude-haiku-5-5`, judge `claude-haiku-5-5`)

Source files: `reports/eval_baseline.md` and `reports/compare_baseline.md` (per-question rows in the `.json`).
Headline = test split (34 questions: 27 answerable, 7 unanswerable). The dev split (16) was used only to calibrate the gate.

| Metric (test split) | Value |
|---|---|
| Retrieval hit rate @1 / @5 | 51.9% / 81.5% (MRR@5 0.614) |
| Quote verification rate (guardrail) | 100% |
| Citation page accuracy | 86.4% |
| Faithfulness (LLM judge, answered questions) | 100% (22 of 22) |
| Answer correctness (answerable) | 81.5% |
| Correct declines | 7 / 7 (10 / 10 over all 50) |
| False decline rate (answerable) | 18.5% |
| Cost per question (answer model) | $0.00031 |
| Latency p50 / p95 | 2.8 s / 4.0 s |

All 50 questions: hit@5 85.0%, correctness 87.5%, faithfulness 100% (35 judged), 10/10 correct declines.

### Before / after (test split, same questions, same models)

| Mode | hit@1 | hit@5 | MRR@5 | Faithfulness | Correctness | Declines | Cost/q | p50 |
|---|---|---|---|---|---|---|---|---|
| vector only (baseline) | 37.0% | 66.7% | 0.472 | 100% | 81.5% | 7/7 | $0.00036 | 1.3 s |
| hybrid BM25 + vector | 48.1% | 77.8% | 0.602 | 100% | 88.9% | 7/7 | $0.00038 | 1.4 s |
| hybrid + re-rank + gate (final) | 51.9% | 81.5% | 0.614 | 100% | 81.5% | 7/7 | $0.00030 | 2.5 s |
| hybrid + re-rank, gate off | 51.9% | 81.5% | 0.614 | 100% | 92.6% | 7/7 | $0.00040 | 2.7 s |

Reading it honestly:
- Hybrid search improves hit@5 from 66.7% to 77.8%, and re-ranking to 81.5% (hit@1 from 37.0% to 51.9% versus
  vector-only), at about +1.2 s latency.
- The relevance gate skipped 8 of 34 LLM calls on the test split (cheaper) but wrongly declined 2 answerable questions,
  so correctness drops from 92.6% (gate off) to 81.5%. The threshold was frozen from the 16 dev questions before looking
  at test, so it was not tuned to fix this. Over all 50 questions, gate-off had one unfaithful answer (faithfulness 97.4%
  versus 100% with the gate). Whether the gate is worth it is a cost-versus-recall choice; set
  `retrieval.decline_threshold` very low to disable it.
- LLM output is not perfectly deterministic: the table above and `eval_baseline.md` are separate runs of the same configuration.
- With 27 answerable test questions, one question is 3.7 points. Treat differences of a few points as noise.

## Cost per run

Measured from token usage x `config/pricing.yaml` ($0.10 / $0.50 per MTok input / output for `claude-haiku-5-5`):
about $0.0003 per question (about 3,000 input and 200 output tokens per call). A full 50-question eval costs $0.015
for answers plus $0.007 for the judge. The four-mode comparison costs roughly $0.1. Ingest is free (local models).
Prompt caching is enabled on the system prompt, but the prompt is too short for the provider to cache it, so the
measured cache-read tokens were 0.

## How to run

```bash
python -m venv .venv && . .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
cp .env.example .env                                  # fill ANTHROPIC_API_KEY
python scripts/download_corpus.py                     # make download
python -m citesure.ingest.cli all                     # make ingest (about 3 min on CPU)
python -m uvicorn citesure.app:app --port 8000        # make serve, open http://127.0.0.1:8000
python -m citesure.eval.run                           # make eval: writes reports/eval_<ts>.{md,json}
python -m citesure.eval.compare --modes vector hybrid hybrid_rerank hybrid_rerank:nogate   # before/after
python -m pytest                                      # make test
```

The first question after start-up takes about 25 s because the embedding and re-rank models load; later ones take about 3 s.

Configuration: `config/settings.yaml` (retrieval mode, k values, decline threshold, limits) and `.env`
(`LLM_PROVIDER`, `LLM_MODEL`, `JUDGE_MODEL`, `ANTHROPIC_API_KEY`, rate limits). The demo limits 10 questions/hour/IP and
200/day, and serves six pre-computed example answers at zero cost (`static/examples.json`).

## Evaluation method

50 questions in `eval/questions.jsonl` (40 answerable: 12 fact, 8 definition, 6 table, 6 paraphrase, 4 multi-hop,
4 cross-document; 10 unanswerable but on-topic), split 16 dev / 34 test. Questions and gold passages were drafted by an
LLM and verified programmatically (the gold passage must occur verbatim at the stated PDF page; unanswerable questions
must use terms absent from the corpus). **No human has reviewed them** (`verified_by_human: false`; reports print a
warning). A hit is a retrieved chunk from the gold document that contains the gold page and passage. Faithfulness and
correctness are judged by `claude-haiku-5-5`, the same model that answers, so bias is possible. See `eval/README.md`.

## Tests

`python -m pytest` runs 51 offline tests (parsing, chunking, retrieval modes, quote verification, retry/decline logic,
gate, prompts, API and rate limit, metrics). The LLM is mocked.

## Limitations

- English, born-digital PDFs only (no OCR); four documents, 329 pages.
- The eval set is small and not human-reviewed; judge and answerer are the same model.
- Hit@5 is 81.5% on test: about one in five answerable questions has no gold chunk in the top 5. Cross-document
  questions are the weakest (clarifying questions instead of answers).
- The gate has a measured cost in false declines (above).
- Page numbers are PDF page indexes, not printed page labels. Complex merged-cell tables may parse imperfectly.
- Not deployed: no Hugging Face token was available. Rate limits are in memory, single process.
- Not legal or compliance advice.

## Data and licence

NIST publications are works of the US Government, not subject to US copyright. Not an official NIST product; no
endorsement implied. Code: MIT. More: `docs/VIDEO_SCRIPT.md`, `docs/UPWORK_ENTRY.md`, `docs/PROJECT_CATALOG.md`.
