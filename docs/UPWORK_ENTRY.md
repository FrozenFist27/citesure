# Upwork portfolio entry (DEMO PROJECT, not client work)

**Title:** CiteSure - Document Q&A Chatbot with Verbatim Citations and an Evaluation Report (Demo Project)

**Label:** Demo project built on public NIST cybersecurity publications. Not client work.

**Role:** Solo - design, build, evaluation.

**Description:**
A chatbot that answers only from a document set, shows the exact quoted passage and a link to the PDF page for
every answer, and says "I don't know" when the documents do not cover the question. Hybrid keyword + vector search with
re-ranking, deterministic quote verification (every shown quote is checked character-for-character against the source),
and a one-command evaluation on 50 questions including 10 unanswerable ones.

Measured results (test split, 34 questions, claude-haiku-5-5, 2026-10-17):
- Retrieval hit rate @5: 81.5% (vector-only baseline 66.7%, hybrid 77.8%)
- Faithfulness (LLM judge): 100% of answered questions (22 of 22)
- Correct declines: 7 of 7 (10 of 10 over all 50)
- Cost: about $0.0003 per question; latency p50 2.8 s
- Honest caveats: the 50 eval questions are LLM-drafted and checked programmatically, not yet reviewed by a human;
  the relevance gate causes some false declines (answer correctness 81.5% with the gate vs 92.6% without, test split).

**Skills:** Python, RAG, LLM, FastAPI, Information Retrieval, Evaluation, Claude API

**Links:** GitHub repo: TBD by owner. Live demo: not deployed. Video: to be recorded from `docs/VIDEO_SCRIPT.md`.

**Media:** screenshot of an answer with quote cards; screenshot of `reports/eval_baseline.md`.
