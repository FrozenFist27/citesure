# Upwork portfolio entry

**Title:** CiteSure - Document Q&A Chatbot with Verbatim Citations and an Evaluation Report

**Label:** Built on public NIST cybersecurity publications.

**Role:** Solo - design, build, evaluation.

**Description:**
A chatbot that answers only from a document set, shows the exact quoted passage and a link to the PDF page for
every answer, and says "I don't know" when the documents do not cover the question. Hybrid keyword + vector search with
re-ranking, deterministic quote verification (every shown quote is checked character-for-character against the source),
and a one-command evaluation on 50 questions including 10 unanswerable ones.

Measured results (test split, 34 questions, claude-haiku-5-5, 2026-10-18, relevance gate off):
- Retrieval hit rate @5: 81.5% (vector-only baseline 66.7%, hybrid 77.8%)
- Faithfulness (LLM judge): 100% of answered questions (25 of 25)
- Correct declines: 7 of 7 (10 of 10 over all 50)
- Answer correctness: 92.6% (false declines 7.4%, 2 of 27)
- Cost: about $0.0004 per question ($0.00039); latency p50 3.9 s
- Honest caveats: the 50 eval questions are LLM-drafted and checked programmatically, not yet reviewed by a human;
  an optional relevance gate (off by default) saved about 25% of cost but caused false declines (ablation: answer correctness 81.5% with the gate vs 92.6% without, test split).

**Skills:** Python, RAG, LLM, FastAPI, Information Retrieval, Evaluation, Claude API

**Links:** GitHub repo: TBD by owner. Live demo: not deployed. Video: to be recorded from `docs/VIDEO_SCRIPT.md`.

**Media:** screenshot of an answer with quote cards; screenshot of `reports/eval_baseline.md`.
