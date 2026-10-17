# Eval set

`questions.jsonl` has 50 questions: 40 answerable (12 fact, 8 definition, 6 table, 6 paraphrase,
4 multi-hop, 4 cross-document) and 10 unanswerable (on-topic but not covered). 16 are the `dev`
split (used only to calibrate the decline threshold), 34 are the `test` split (headline numbers).

How it was made (honest version):
- The questions, gold answers and gold passages were drafted by an LLM (Claude) reading the
  ingested corpus. They are built by `scripts/build_eval_set.py`, which keeps the drafts in code.
- **Verification is programmatic, not human**: the script fails unless every gold passage occurs
  verbatim (whitespace/quote-normalised) in the extracted text of the stated document, and the PDF
  page is derived from where the passage occurs. For unanswerable questions it fails if the corpus
  contains key terms of the question.
- Every item has `"verified_by_human": false`. Reports print a warning. A human should review the
  gold answers before the set is used to make claims to a client.
- Retrieval hit: a retrieved chunk from the gold document whose page range contains the gold page
  and that contains the gold passage (exact, or >= 50% of its word trigrams). Multi-hop and
  cross-document questions need every gold passage retrieved.
