# CiteSure eval report (baseline: mode=hybrid_rerank, one command: `python -m citesure.eval.run`)

- Timestamp: 2026-10-18T10:56:04Z  |  git commit: `131bec4`
- Answer model: `claude-haiku-5-5`  |  judge model: `claude-haiku-5-5`
- Settings: {"mode": "hybrid_rerank", "bm25_k": 20, "vector_k": 20, "rrf_k": 60, "rerank_top_n": 20, "final_k": 5, "gate_enabled": false, "decline_threshold": 0.1}
- Eval file sha256: `dd27db5165baf787...`  |  corpus sha256: csf-2.0=`3c31f46f`, sp800-61r3=`e5593d6b`, sp800-171r3=`3e4631df`, sp800-63b-4=`d9ab8957`
- Questions not verified by a human: 50 of 50 (drafted by an LLM, gold passages verified programmatically against the PDF text; see eval/README.md)

## Test split (headline, 34 questions)

| Metric | Value |
|---|---|
| Questions (answerable / unanswerable) | 34 (27 / 7) |
| Retrieval hit rate @1 | 51.9% |
| Retrieval hit rate @5 | 81.5% |
| MRR@5 | 0.614 |
| Quote verification rate (guardrail) | 100.0% |
| Citation page accuracy | 80.0% |
| Faithfulness (LLM judge, answered questions) | 100.0% (n=25) |
| Answer correctness (answerable) | 92.6% |
| Correct declines | 7 / 7 |
| False decline rate (answerable) | 7.4% |
| Cost per question (answer model) | $0.00039 |
| Total answer cost | $0.01335 |
| Judge cost (reported separately) | $0.00469 |
| Latency p50 / p95 | 3,912 ms / 6,652 ms |
| Mean latency by stage | retrieve 2653.7 ms, rerank 2774.3 ms, llm 1571.9 ms, verify 2.8 ms |

## Dev split (16 questions, used to calibrate the gate)

| Metric | Value |
|---|---|
| Questions (answerable / unanswerable) | 16 (13 / 3) |
| Retrieval hit rate @1 | 46.2% |
| Retrieval hit rate @5 | 92.3% |
| MRR@5 | 0.641 |
| Quote verification rate (guardrail) | 100.0% |
| Citation page accuracy | 84.6% |
| Faithfulness (LLM judge, answered questions) | 92.3% (n=13) |
| Answer correctness (answerable) | 100.0% |
| Correct declines | 3 / 3 |
| False decline rate (answerable) | 0.0% |
| Cost per question (answer model) | $0.00039 |
| Total answer cost | $0.00630 |
| Judge cost (reported separately) | $0.00272 |
| Latency p50 / p95 | 4,015 ms / 6,601 ms |
| Mean latency by stage | retrieve 84.0 ms, rerank 2737.0 ms, llm 1475.8 ms, verify 3.8 ms |

## All 50 questions

| Metric | Value |
|---|---|
| Questions (answerable / unanswerable) | 50 (40 / 10) |
| Retrieval hit rate @1 | 50.0% |
| Retrieval hit rate @5 | 85.0% |
| MRR@5 | 0.622 |
| Quote verification rate (guardrail) | 100.0% |
| Citation page accuracy | 81.6% |
| Faithfulness (LLM judge, answered questions) | 97.4% (n=38) |
| Answer correctness (answerable) | 95.0% |
| Correct declines | 10 / 10 |
| False decline rate (answerable) | 5.0% |
| Cost per question (answer model) | $0.00039 |
| Total answer cost | $0.01965 |
| Judge cost (reported separately) | $0.00741 |
| Latency p50 / p95 | 3,946 ms / 7,266 ms |
| Mean latency by stage | retrieve 1831.4 ms, rerank 2762.4 ms, llm 1541.1 ms, verify 3.1 ms |

## Per-question results

| id | cat | split | status | gold rank | ms | faithful | correct |
|---|---|---|---|---|---|---|---|
| q001 | fact | test | answered | 1 | 96986 | 1 | 1 |
| q002 | fact | dev | answered | 3 | 4219 | 0 | 1 |
| q003 | fact | test | answered | 1 | 3753 | 1 | 1 |
| q004 | fact | test | answered | 1 | 3061 | 1 | 1 |
| q005 | fact | dev | answered | 1 | 3457 | 1 | 1 |
| q006 | fact | test | answered | 1 | 4310 | 1 | 1 |
| q007 | fact | test | answered | 1 | 7266 | 1 | 1 |
| q008 | fact | dev | answered | 1 | 7472 | 1 | 1 |
| q009 | fact | test | answered | 2 | 4626 | 1 | 1 |
| q010 | fact | test | answered | 1 | 6652 | 1 | 1 |
| q011 | fact | dev | answered | 2 | 3961 | 1 | 1 |
| q012 | fact | test | answered | 1 | 4396 | 1 | 1 |
| q013 | definition | test | answered | 1 | 3931 | 1 | 1 |
| q014 | definition | dev | answered | 1 | 3504 | 1 | 1 |
| q015 | definition | test | answered | 1 | 3618 | 1 | 1 |
| q016 | definition | test | answered | 4 | 3875 | 1 | 1 |
| q017 | definition | dev | answered | 1 | 6601 | 1 | 1 |
| q018 | definition | test | answered | 5 | 4437 | 1 | 1 |
| q019 | definition | test | answered | 1 | 4687 | 1 | 1 |
| q020 | definition | dev | answered | 2 | 4111 | 1 | 1 |
| q021 | table | test | answered | - | 6309 | 1 | 1 |
| q022 | table | test | answered | 3 | 5200 | 1 | 1 |
| q023 | table | dev | answered | 4 | 3688 | 1 | 1 |
| q024 | table | test | answered | 5 | 3549 | 1 | 1 |
| q025 | table | test | answered | 3 | 3639 | 1 | 1 |
| q026 | table | dev | answered | 4 | 3826 | 1 | 1 |
| q027 | paraphrase | test | answered | - | 5840 | 1 | 1 |
| q028 | paraphrase | test | answered | 1 | 3877 | 1 | 1 |
| q029 | paraphrase | dev | answered | 1 | 3771 | 1 | 1 |
| q030 | paraphrase | test | answered | 1 | 3893 | 1 | 1 |
| q031 | paraphrase | test | answered | 1 | 4040 | 1 | 1 |
| q032 | paraphrase | dev | answered | 1 | 3826 | 1 | 1 |
| q033 | multi-hop | test | answered | - | 4924 | 1 | 1 |
| q034 | multi-hop | test | answered | 2 | 3588 | 1 | 1 |
| q035 | multi-hop | dev | answered | 2 | 4368 | 1 | 1 |
| q036 | multi-hop | test | answered | 1 | 4089 | 1 | 1 |
| q037 | cross-document | test | answered | 4 | 3717 | 1 | 1 |
| q038 | cross-document | dev | answered | - | 4405 | 1 | 1 |
| q039 | cross-document | test | clarify | - | 3750 | None | 0 |
| q040 | cross-document | test | declined | - | 2970 | None | 0 |
| q041 | unanswerable | dev | declined | - | 3200 | None | None |
| q042 | unanswerable | test | declined | - | 3793 | None | None |
| q043 | unanswerable | test | declined | - | 3378 | None | None |
| q044 | unanswerable | test | declined | - | 3385 | None | None |
| q045 | unanswerable | dev | declined | - | 4484 | None | None |
| q046 | unanswerable | test | declined | - | 3821 | None | None |
| q047 | unanswerable | test | declined | - | 3774 | None | None |
| q048 | unanswerable | test | declined | - | 4457 | None | None |
| q049 | unanswerable | dev | declined | - | 4068 | None | None |
| q050 | unanswerable | test | declined | - | 4783 | None | None |
