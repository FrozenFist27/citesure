# CiteSure demo video script (under 2 minutes)

Label on screen the whole time: "Demo project on public NIST documents. Not client work."
All numbers come from `reports/eval_baseline.md` and `reports/compare_baseline.md` (2026-10-17 run).

| Time | Shot | Voice-over |
|---|---|---|
| 0:00-0:10 | Title card "CiteSure" | "Document chatbots make things up. This one shows proof for every answer, or says it does not know." |
| 0:10-0:35 | Click the example "What minimum password length must verifiers require..." Hover the quote card, click "page N": the PDF opens at that page. | "Each sentence has a verbatim quote, checked by code against the source, and a link to the exact page." |
| 0:35-0:50 | Click the example about CSF Tiers or wireless access. | "It reads headings and tables, not just paragraphs." |
| 0:50-1:05 | Click "How much does a YubiKey 5 hardware authenticator cost?" The decline card shows the closest sections checked. | "If the documents do not say it, it says I do not know, and shows where it looked." |
| 1:05-1:45 | Terminal: `python -m citesure.eval.run`, then open `reports/eval_baseline.md`: test hit@5 81.5%, faithfulness 100%, declines 7 of 7, cost $0.00031 per question, p50 2.8 s. Then `compare_baseline.md`: hit@5 vector 66.7%, hybrid 77.8%, re-rank 81.5%. | "One command measures it on 50 questions: retrieval hit rate, faithfulness, correct declines, cost and latency. Hybrid search and re-ranking lifted hit rate at five from 67 to 82 percent. The questions are LLM-drafted and not yet human-reviewed, and the report says so." |
| 1:45-2:00 | Architecture diagram, then contact slide. | "Want this on your documents? Message me." |
