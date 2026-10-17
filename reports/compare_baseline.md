# CiteSure before/after: retrieval modes and gate

Same 50 questions, same answer and judge model (`claude-haiku-5-5`); only retrieval mode (or the relevance gate) changes. Headline = test split. `hybrid_rerank` runs with the dev-calibrated gate (threshold 0.1); `hybrid_rerank:nogate` is the same pipeline with the gate disabled. LLM output is not perfectly deterministic, so small differences between this table and `eval_baseline.md` (a separate run of the same final configuration) are run-to-run noise.

Timestamp 2026-10-17T18:45:50Z, commit `badad54`, answer model `claude-haiku-5-5`.

## Split: test

| Mode | hit@1 | hit@5 | MRR@5 | Faithfulness | Correctness | Correct declines | Cost/question | p50 latency |
|---|---|---|---|---|---|---|---|---|
| vector | 37.0% | 66.7% | 0.472 | 100.0% | 81.5% | 7/7 | $0.00036 | 1,299 ms |
| hybrid | 48.1% | 77.8% | 0.602 | 100.0% | 88.9% | 7/7 | $0.00038 | 1,358 ms |
| hybrid_rerank | 51.9% | 81.5% | 0.614 | 100.0% | 81.5% | 7/7 | $0.00030 | 2,524 ms |
| hybrid_rerank:nogate | 51.9% | 81.5% | 0.614 | 100.0% | 92.6% | 7/7 | $0.00040 | 2,703 ms |

## Split: dev

| Mode | hit@1 | hit@5 | MRR@5 | Faithfulness | Correctness | Correct declines | Cost/question | p50 latency |
|---|---|---|---|---|---|---|---|---|
| vector | 38.5% | 76.9% | 0.518 | 100.0% | 100.0% | 3/3 | $0.00035 | 1,374 ms |
| hybrid | 38.5% | 76.9% | 0.551 | 100.0% | 100.0% | 3/3 | $0.00037 | 1,349 ms |
| hybrid_rerank | 46.2% | 92.3% | 0.641 | 100.0% | 100.0% | 3/3 | $0.00032 | 2,715 ms |
| hybrid_rerank:nogate | 46.2% | 92.3% | 0.641 | 92.3% | 100.0% | 3/3 | $0.00038 | 2,867 ms |

## Split: all

| Mode | hit@1 | hit@5 | MRR@5 | Faithfulness | Correctness | Correct declines | Cost/question | p50 latency |
|---|---|---|---|---|---|---|---|---|
| vector | 37.5% | 70.0% | 0.487 | 100.0% | 87.5% | 10/10 | $0.00036 | 1,316 ms |
| hybrid | 45.0% | 77.5% | 0.585 | 100.0% | 92.5% | 10/10 | $0.00037 | 1,358 ms |
| hybrid_rerank | 50.0% | 85.0% | 0.622 | 100.0% | 87.5% | 10/10 | $0.00031 | 2,624 ms |
| hybrid_rerank:nogate | 50.0% | 85.0% | 0.622 | 97.4% | 95.0% | 10/10 | $0.00039 | 2,745 ms |
