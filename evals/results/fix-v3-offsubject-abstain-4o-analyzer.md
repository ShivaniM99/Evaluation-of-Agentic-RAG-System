# Eval run `fix-v3-offsubject-abstain-4o-analyzer`

- version `b53be8c` · generator `{'planner': 'gpt-4o-mini', 'analyzer': 'gpt-4o', 'refiner': 'gpt-4o-mini', 'synthesizer': 'gpt-4o-mini', 'verifier': 'gpt-4o-mini'}` · judge `anthropic:claude-sonnet-5-5`
- items 30 (0 errors) · pipeline cost $0.293 · judge cost $0.751 (64 calls, 41 cached) · latency p50 17.198s / p95 25.917s

## Metrics

| metric | mean | 95% CI | n |
|---|---|---|---|
| retrieval.recall@5 | 86.5% | 71.9% – 96.9% | 24 |
| retrieval.precision@5 | 53.5% | 40.5% – 67.3% | 24 |
| retrieval.mrr | 0.788 | 0.639 – 0.917 | 24 |
| retrieval.ndcg@5 | 0.806 | 0.659 – 0.926 | 24 |
| retrieval.hit@5 | 87.5% | 72.9% – 97.9% | 24 |
| retrieval.doc_hit@5 | 91.7% | 81.2% – 100.0% | 24 |
| retrieval.context_precision | 60.6% | 47.9% – 74.0% | 24 |
| generation.groundedness | 94.6% | 88.2% – 98.8% | 23 |
| generation.citation_precision | 76.1% | 62.5% – 89.2% | 23 |
| generation.citation_recall | 65.9% | 50.7% – 80.6% | 23 |
| generation.citation_validity | 100.0% | 100.0% – 100.0% | 21 |
| correctness.correctness | 84.1% | 71.1% – 93.8% | 24 |
| correctness.fact_coverage | 84.0% | 70.1% – 94.4% | 24 |
| correctness.relevance | 91.4% | 82.8% – 97.2% | 24 |
| abstention.abstention_correct | 95.0% | 86.7% – 100.0% | 30 |
| abstention.false_abstain | 5.0% | 0.0% – 13.3% | 30 |
| abstention.hallucinated_answer | 0.0% | 0.0% – 0.0% | 30 |
| trajectory.iterations | 1.117 | 0.667 – 1.617 | 30 |
| trajectory.terminated_sufficient | 71.7% | 55.0% – 86.7% | 30 |
| trajectory.hit_max_iterations | 28.3% | 13.3% – 45.0% | 30 |
| trajectory.refiner_helped | 25.0% | 6.2% – 50.0% | 8 |
| trajectory.refiner_recall_gain | 0.219 | 0.031 – 0.469 | 8 |
| trajectory.analyzer_decision_correct | 98.3% | 95.0% – 100.0% | 30 |
| trajectory.cost_usd | 0.010 | 0.008 – 0.012 | 30 |
| trajectory.llm_calls | 21.633 | 18.150 – 25.367 | 30 |
| trajectory.had_error | 0.0% | 0.0% – 0.0% | 30 |

## Run-to-run stability (2 repeats per question)

- abstain/answer flips between repeats: 3.3% of questions
- retrieved chunk set differs between repeats: 43.3% of questions
- mean within-question std: correctness 0.060, groundedness 0.020, recall@5 0.044

Differences between two runs smaller than this spread are noise.

## By question type

| type | n | groundedness | citation_precision | citation_recall | correctness | recall@5 | mrr | abstention_correct |
|---|---|---|---|---|---|---|---|---|
| multi-hop | 8 | 97.7% | 74.2% | 58.4% | 79.7% | 81.2% | 0.729 | 100.0% |
| procedural | 9 | 92.2% | 67.4% | 52.8% | 93.1% | 100.0% | 0.935 | 100.0% |
| release-notes | 6 | 92.9% | 90.1% | 94.6% | 83.3% | 83.3% | 0.750 | 83.3% |
| single-hop | 1 | 100.0% | 100.0% | 100.0% | 42.5% | 25.0% | 0.167 | 50.0% |
| unanswerable | 6 | – | – | – | – | – | – | 100.0% |

## Mean node latency (s)

- planner: 1.16
- retriever: 7.34
- analyzer: 3.75
- refiner: 2.56
- synthesizer: 2.95
- verifier: 3.02
