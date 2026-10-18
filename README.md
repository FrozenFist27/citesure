# CiteSure

**Answers from your documents, with the exact quote and page, or an honest "I don't know".**

> Built on public NIST documents.
> **Live demo:** https://citesure-h4efwpcu7q-uc.a.run.app (example questions answer instantly; the first typed question after idle can take about a minute while models load; 100 questions/day cap).
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
- Unanswerable questions are declined by the answer model itself ("I don't know" JSON status) and by the quote
  verifier. An optional relevance gate (`retrieval.gate_enabled: true`, off by default) can decline earlier without
  calling the LLM. Declines list the closest sections checked. Ambiguous questions get a clarifying question.
- One-command evaluation report and a before/after comparison.

Corpus (329 pages, public US-government works): NIST CSF 2.0, SP 800-61r3, SP 800-171r3, SP 800-63B-4
(886 chunks, 153 of them tables).

## Architecture

```
 data/raw/*.pdf -> parse.py -> chunk.py -> index/ (SQLite chunks, BM25 pickle, embeddings .npy)

 question -> BM25 top20 + vector top20 -> RRF -> cross-encoder re-rank -> top5
          -> [optional gate, off by default: best score < threshold: DECLINE, no LLM call]
          -> LLM JSON answer (quote per sentence) -> verify quotes (exact substring) -> retry once -> answer | decline
 FastAPI: GET / (chat page), POST /api/ask, GET /docs/{doc}.pdf#page=N, GET /api/health
 eval:    python -m citesure.eval.run  ->  reports/eval_<ts>.{md,json}
```

## Results (real run, 2026-10-18, commit `131bec4`, gate off, model `claude-haiku-5-5`, judge `claude-haiku-5-5`)

Source files: `reports/eval_baseline.md` (final configuration, gate off), `reports/eval_baseline_gate_on.md` (previous run, gate on) and
`reports/compare_baseline.md` (per-question rows in the `.json`).
Headline = test split (34 questions: 27 answerable, 7 unanswerable). The dev split (16) was used only to calibrate the (now optional) gate.

| Metric (test split) | Value |
|---|---|
| Retrieval hit rate @1 / @5 | 51.9% / 81.5% (MRR@5 0.614) |
| Quote verification rate (guardrail) | 100% |
| Citation page accuracy | 80.0% |
| Faithfulness (LLM judge, answered questions) | 100% (25 of 25) |
| Answer correctness (answerable) | 92.6% |
| Correct declines | 7 / 7 (10 / 10 over all 50) |
| False decline rate (answerable) | 7.4% (2 of 27: 1 decline, 1 clarifying question) |
| Cost per question (answer model) | $0.00039 |
| Latency p50 / p95 | 3.9 s / 6.7 s |

All 50 questions: hit@5 85.0%, correctness 95.0%, faithfulness 97.4% (38 judged; one unfaithful answer, q002), 10/10 correct declines.
For reference, the previous gate-on run (`eval_baseline_gate_on.md`) had all-50 correctness 87.5%, faithfulness 100% (35 judged), $0.00031 per question.

### Before / after (test split, same questions, same models)

| Mode | hit@1 | hit@5 | MRR@5 | Faithfulness | Correctness | Declines | Cost/q | p50 |
|---|---|---|---|---|---|---|---|---|
| vector only (baseline) | 37.0% | 66.7% | 0.472 | 100% | 81.5% | 7/7 | $0.00036 | 1.3 s |
| hybrid BM25 + vector | 48.1% | 77.8% | 0.602 | 100% | 88.9% | 7/7 | $0.00038 | 1.4 s |
| hybrid + re-rank, gate off (final, `eval_baseline.md`) | 51.9% | 81.5% | 0.614 | 100% | 92.6% | 7/7 | $0.00039 | 3.9 s |
| ablation: hybrid + re-rank, gate on (`compare_baseline.md`) | 51.9% | 81.5% | 0.614 | 100% | 81.5% | 7/7 | $0.00030 | 2.5 s |

Reading it honestly:
- Hybrid search improves hit@5 from 66.7% to 77.8%, and re-ranking to 81.5% (hit@1 from 37.0% to 51.9% versus
  vector-only), at about +1.2 s latency.
- The relevance gate is OFF by default (owner decision). With the gate on, it skipped 8 of 34 LLM calls on the test split
  (about 25% cheaper, $0.00030 versus $0.00040 per question in that comparison run) but wrongly declined 2 answerable
  questions, so correctness dropped from 92.6% to 81.5%. The threshold was frozen from the 16 dev questions before looking
  at test. Without the gate, unanswerable questions are still declined correctly (7/7 test, 10/10 over all 50) by the
  answer model itself. Gate-off had one unfaithful answer over all 50 (faithfulness 97.4% versus 100% with the gate).
  Re-enable with `retrieval.gate_enabled: true`.
- Latency in the final gate-off run (p50 3.9 s) is higher than the earlier runs (2.5-2.8 s) because the local
  retrieve stage was slower in that run (mean 2.7 s versus 0.3 s on the 2026-10-17 re-run); the LLM stage was 1.6 s. Treat
  latency as machine-dependent.
- LLM output is not perfectly deterministic: the table above and `eval_baseline.md` are separate runs of the same configuration.
- Re-run check (a second full run of the same command, not committed): all-50 hit@5 85.0% (identical, retrieval is deterministic), correctness 90.0% (baseline 87.5%), faithfulness 97.2% over 36 judged (baseline 100% over 35), 10/10 correct declines, $0.00030 per question. Retrieval numbers reproduce exactly; LLM-dependent numbers move by a few points between runs.
- With 27 answerable test questions, one question is 3.7 points. Treat differences of a few points as noise.

## Cost per run

Measured from token usage x `config/pricing.yaml` ($0.10 / $0.50 per MTok input / output for `claude-haiku-5-5`):
about $0.0004 per question with the gate off (about $0.0003 with it on; about 3,000 input and 200 output tokens per call). A full 50-question eval costs $0.020
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
python -m citesure.eval.compare --modes vector hybrid hybrid_rerank:nogate hybrid_rerank:gate   # before/after (gate ablation)
python -m pytest                                      # make test
```

The first question after start-up takes about 25 s because the embedding and re-rank models load; later ones take about 3 s.

Configuration: `config/settings.yaml` (retrieval mode, k values, `gate_enabled`, decline threshold, limits) and `.env`
(`LLM_PROVIDER`, `LLM_MODEL`, `JUDGE_MODEL`, `ANTHROPIC_API_KEY`, rate limits). The demo limits 10 live questions/hour/IP and
100/day globally (`DEMO_DAILY_QUESTION_CAP`, `RATE_LIMIT_PER_IP_PER_HOUR`), and serves six pre-computed example answers at zero cost (`static/examples.json`).

## Evaluation method

50 questions in `eval/questions.jsonl` (40 answerable: 12 fact, 8 definition, 6 table, 6 paraphrase, 4 multi-hop,
4 cross-document; 10 unanswerable but on-topic), split 16 dev / 34 test. Questions and gold passages were drafted by an
LLM and verified programmatically (the gold passage must occur verbatim at the stated PDF page; unanswerable questions
must use terms absent from the corpus). **No human has reviewed them** (`verified_by_human: false`; reports print a
warning). A hit is a retrieved chunk from the gold document that contains the gold page and passage. Faithfulness and
correctness are judged by `claude-haiku-5-5`, the same model that answers, so bias is possible. See `eval/README.md`.

## Tests

`python -m pytest` runs 52 offline tests (parsing, chunking, retrieval modes, quote verification, retry/decline logic,
gate, prompts, API and rate limit, metrics). The LLM is mocked.

## Limitations

- English, born-digital PDFs only (no OCR); four documents, 329 pages.
- The eval set is small and not human-reviewed; judge and answerer are the same model.
- Hit@5 is 81.5% on test: about one in five answerable questions has no gold chunk in the top 5. Cross-document
  questions are the weakest (clarifying questions instead of answers).
- The optional gate (off by default) has a measured cost in false declines (above); without it every question costs an LLM call.
- Page numbers are PDF page indexes, not printed page labels. Complex merged-cell tables may parse imperfectly.
- Hosted on Google Cloud Run (us-central1, 2 vCPU / 2 GiB, scales to zero, max 1 instance). The first typed question after idle measured 69 s (model loading); warm questions 5-6 s. Rate limits are in memory and reset when the instance restarts.
- Not legal or compliance advice.

## Data and licence

NIST publications are works of the US Government, not subject to US copyright. Not an official NIST product; no
endorsement implied. Code: MIT. More: `docs/VIDEO_SCRIPT.md`, `docs/UPWORK_ENTRY.md`, `docs/PROJECT_CATALOG.md`.
