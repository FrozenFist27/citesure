# CiteSure eval report (baseline: mode=hybrid_rerank, one command: `python -m citesure.eval.run`)

- Timestamp: 2026-10-17T18:42:11Z  |  git commit: `badad54`
- Answer model: `claude-haiku-5-5`  |  judge model: `claude-haiku-5-5`
- Settings: {"mode": "hybrid_rerank", "bm25_k": 20, "vector_k": 20, "rrf_k": 60, "rerank_top_n": 20, "final_k": 5, "decline_threshold": 0.1}
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
| Citation page accuracy | 86.4% |
| Faithfulness (LLM judge, answered questions) | 100.0% (n=22) |
| Answer correctness (answerable) | 81.5% |
| Correct declines | 7 / 7 |
| False decline rate (answerable) | 18.5% |
| Cost per question (answer model) | $0.00031 |
| Total answer cost | $0.01042 |
| Judge cost (reported separately) | $0.00406 |
| Latency p50 / p95 | 2,793 ms / 3,998 ms |
| Mean latency by stage | retrieve 499.8 ms, rerank 1649.4 ms, llm 1147.4 ms, verify 1.1 ms |

## Dev split (16 questions, used to calibrate the gate)

| Metric | Value |
|---|---|
| Questions (answerable / unanswerable) | 16 (13 / 3) |
| Retrieval hit rate @1 | 46.2% |
| Retrieval hit rate @5 | 92.3% |
| MRR@5 | 0.641 |
| Quote verification rate (guardrail) | 100.0% |
| Citation page accuracy | 84.6% |
| Faithfulness (LLM judge, answered questions) | 100.0% (n=13) |
| Answer correctness (answerable) | 100.0% |
| Correct declines | 3 / 3 |
| False decline rate (answerable) | 0.0% |
| Cost per question (answer model) | $0.00031 |
| Total answer cost | $0.00504 |
| Judge cost (reported separately) | $0.00269 |
| Latency p50 / p95 | 2,852 ms / 3,165 ms |
| Mean latency by stage | retrieve 41.4 ms, rerank 1504.2 ms, llm 1133.7 ms, verify 1.8 ms |

## All 50 questions

| Metric | Value |
|---|---|
| Questions (answerable / unanswerable) | 50 (40 / 10) |
| Retrieval hit rate @1 | 50.0% |
| Retrieval hit rate @5 | 85.0% |
| MRR@5 | 0.622 |
| Quote verification rate (guardrail) | 100.0% |
| Citation page accuracy | 85.7% |
| Faithfulness (LLM judge, answered questions) | 100.0% (n=35) |
| Answer correctness (answerable) | 87.5% |
| Correct declines | 10 / 10 |
| False decline rate (answerable) | 12.5% |
| Cost per question (answer model) | $0.00031 |
| Total answer cost | $0.01545 |
| Judge cost (reported separately) | $0.00675 |
| Latency p50 / p95 | 2,793 ms / 3,998 ms |
| Mean latency by stage | retrieve 353.1 ms, rerank 1603.0 ms, llm 1143.0 ms, verify 1.3 ms |

## Per-question results

| id | cat | split | status | gold rank | ms | faithful | correct |
|---|---|---|---|---|---|---|---|
| q001 | fact | test | answered | 1 | 25155 | 1 | 1 |
| q002 | fact | dev | answered | 3 | 3099 | 1 | 1 |
| q003 | fact | test | answered | 1 | 2925 | 1 | 1 |
| q004 | fact | test | answered | 1 | 2092 | 1 | 1 |
| q005 | fact | dev | answered | 1 | 2929 | 1 | 1 |
| q006 | fact | test | answered | 1 | 2612 | 1 | 1 |
| q007 | fact | test | answered | 1 | 2947 | 1 | 1 |
| q008 | fact | dev | answered | 1 | 2391 | 1 | 1 |
| q009 | fact | test | answered | 2 | 2211 | 1 | 1 |
| q010 | fact | test | answered | 1 | 4190 | 1 | 1 |
| q011 | fact | dev | answered | 2 | 2958 | 1 | 1 |
| q012 | fact | test | answered | 1 | 2974 | 1 | 1 |
| q013 | definition | test | answered | 1 | 2776 | 1 | 1 |
| q014 | definition | dev | answered | 1 | 2398 | 1 | 1 |
| q015 | definition | test | answered | 1 | 2918 | 1 | 1 |
| q016 | definition | test | answered | 4 | 3074 | 1 | 1 |
| q017 | definition | dev | answered | 1 | 2738 | 1 | 1 |
| q018 | definition | test | answered | 5 | 2968 | 1 | 1 |
| q019 | definition | test | declined | 1 | 1509 | None | 0 |
| q020 | definition | dev | answered | 2 | 3165 | 1 | 1 |
| q021 | table | test | declined | - | 3998 | None | 0 |
| q022 | table | test | answered | 3 | 2604 | 1 | 1 |
| q023 | table | dev | answered | 4 | 2522 | 1 | 1 |
| q024 | table | test | answered | 5 | 2530 | 1 | 1 |
| q025 | table | test | answered | 3 | 2777 | 1 | 1 |
| q026 | table | dev | answered | 4 | 2775 | 1 | 1 |
| q027 | paraphrase | test | answered | - | 2903 | 1 | 1 |
| q028 | paraphrase | test | answered | 1 | 2810 | 1 | 1 |
| q029 | paraphrase | dev | answered | 1 | 2945 | 1 | 1 |
| q030 | paraphrase | test | answered | 1 | 3030 | 1 | 1 |
| q031 | paraphrase | test | declined | 1 | 1345 | None | 0 |
| q032 | paraphrase | dev | answered | 1 | 2964 | 1 | 1 |
| q033 | multi-hop | test | answered | - | 2969 | 1 | 1 |
| q034 | multi-hop | test | answered | 2 | 2882 | 1 | 1 |
| q035 | multi-hop | dev | answered | 2 | 3089 | 1 | 1 |
| q036 | multi-hop | test | answered | 1 | 2935 | 1 | 1 |
| q037 | cross-document | test | answered | 4 | 3032 | 1 | 1 |
| q038 | cross-document | dev | answered | - | 3350 | 1 | 1 |
| q039 | cross-document | test | clarify | - | 2809 | None | 0 |
| q040 | cross-document | test | clarify | - | 2738 | None | 0 |
| q041 | unanswerable | dev | declined | - | 1874 | None | None |
| q042 | unanswerable | test | declined | - | 1994 | None | None |
| q043 | unanswerable | test | declined | - | 2079 | None | None |
| q044 | unanswerable | test | declined | - | 2109 | None | None |
| q045 | unanswerable | dev | declined | - | 1971 | None | None |
| q046 | unanswerable | test | declined | - | 1831 | None | None |
| q047 | unanswerable | test | declined | - | 2713 | None | None |
| q048 | unanswerable | test | declined | - | 1887 | None | None |
| q049 | unanswerable | dev | declined | - | 1802 | None | None |
| q050 | unanswerable | test | declined | - | 1953 | None | None |
