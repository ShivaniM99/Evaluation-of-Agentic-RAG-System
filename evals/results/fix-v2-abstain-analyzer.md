# Eval run `fix-v2-abstain-analyzer`

- version `b53be8c` · generator `{'planner': 'gpt-4o-mini', 'analyzer': 'gpt-4o-mini', 'refiner': 'gpt-4o-mini', 'synthesizer': 'gpt-4o-mini', 'verifier': 'gpt-4o-mini'}` · judge `anthropic:claude-sonnet-5-5`
- items 30 (0 errors) · pipeline cost $0.043 · judge cost $0.885 (86 calls, 21 cached) · latency p50 14.424s / p95 24.774s

## Metrics

| metric | mean | 95% CI | n |
|---|---|---|---|
| retrieval.recall@5 | 79.2% | 62.5% – 95.8% | 24 |
| retrieval.precision@5 | 47.6% | 32.4% – 64.0% | 24 |
| retrieval.mrr | 0.680 | 0.513 – 0.835 | 24 |
| retrieval.ndcg@5 | 0.708 | 0.546 – 0.856 | 24 |
| retrieval.hit@5 | 79.2% | 62.5% – 95.8% | 24 |
| retrieval.doc_hit@5 | 83.3% | 66.7% – 95.8% | 24 |
| retrieval.context_precision | 56.2% | 40.3% – 71.9% | 24 |
| generation.groundedness | 95.0% | 88.7% – 98.9% | 25 |
| generation.citation_precision | 79.1% | 65.3% – 90.7% | 25 |
| generation.citation_recall | 66.0% | 51.8% – 79.8% | 25 |
| generation.citation_validity | 99.6% | 98.7% – 100.0% | 23 |
| correctness.correctness | 74.4% | 58.5% – 88.0% | 24 |
| correctness.fact_coverage | 73.6% | 56.9% – 88.2% | 24 |
| correctness.relevance | 83.8% | 71.9% – 93.5% | 24 |
| abstention.abstention_correct | 86.7% | 73.3% – 96.7% | 30 |
| abstention.false_abstain | 8.3% | 0.0% – 20.0% | 30 |
| abstention.hallucinated_answer | 5.0% | 0.0% – 13.3% | 30 |
| trajectory.iterations | 0.867 | 0.433 – 1.367 | 30 |
| trajectory.terminated_sufficient | 75.0% | 58.3% – 90.0% | 30 |
| trajectory.hit_max_iterations | 25.0% | 10.0% – 41.7% | 30 |
| trajectory.refiner_helped | 0.0% | 0.0% – 0.0% | 5 |
| trajectory.refiner_recall_gain | 0.000 | 0.000 – 0.000 | 5 |
| trajectory.analyzer_decision_correct | 88.3% | 76.7% – 98.3% | 30 |
| trajectory.cost_usd | 0.001 | 0.001 – 0.002 | 30 |
| trajectory.llm_calls | 19.583 | 16.267 – 23.350 | 30 |
| trajectory.had_error | 0.0% | 0.0% – 0.0% | 30 |

## Run-to-run stability (2 repeats per question)

- abstain/answer flips between repeats: 10.0% of questions
- retrieved chunk set differs between repeats: 36.7% of questions
- mean within-question std: correctness 0.021, groundedness 0.020, recall@5 0.000

Differences between two runs smaller than this spread are noise.

## By question type

| type | n | groundedness | citation_precision | citation_recall | correctness | recall@5 | mrr | abstention_correct |
|---|---|---|---|---|---|---|---|---|
| multi-hop | 8 | 96.1% | 87.6% | 61.7% | 55.3% | 62.5% | 0.536 | 93.8% |
| procedural | 9 | 92.2% | 55.0% | 39.7% | 93.6% | 100.0% | 0.863 | 100.0% |
| release-notes | 6 | 95.0% | 96.3% | 100.0% | 83.3% | 83.3% | 0.708 | 83.3% |
| single-hop | 1 | – | – | – | 0.0% | 0.0% | 0.000 | 0.0% |
| unanswerable | 6 | 100.0% | 100.0% | 100.0% | – | – | – | 75.0% |

## Mean node latency (s)

- planner: 1.13
- retriever: 6.60
- analyzer: 2.35
- refiner: 2.93
- synthesizer: 3.17
- verifier: 3.14
