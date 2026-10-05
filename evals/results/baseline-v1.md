# Eval run `baseline-v1`

- version `b53be8c` · generator `{'planner': 'gpt-4o-mini', 'analyzer': 'gpt-4o-mini', 'refiner': 'gpt-4o-mini', 'synthesizer': 'gpt-4o-mini', 'verifier': 'gpt-4o-mini'}` · judge `anthropic:claude-sonnet-5-5`
- items 30 (0 errors) · pipeline cost $0.043 · judge cost $1.100 (108 calls, 1 cached) · latency p50 15.247s / p95 29.235s

## Metrics

| metric | mean | 95% CI | n |
|---|---|---|---|
| retrieval.recall@5 | 81.2% | 64.6% – 95.8% | 24 |
| retrieval.precision@5 | 47.1% | 33.7% – 61.8% | 24 |
| retrieval.mrr | 0.672 | 0.517 – 0.818 | 24 |
| retrieval.ndcg@5 | 0.708 | 0.553 – 0.848 | 24 |
| retrieval.hit@5 | 81.2% | 64.6% – 95.8% | 24 |
| retrieval.doc_hit@5 | 85.4% | 70.8% – 97.9% | 24 |
| retrieval.context_precision | 55.3% | 41.0% – 69.5% | 24 |
| generation.groundedness | 93.6% | 87.3% – 97.6% | 25 |
| generation.citation_precision | 79.0% | 64.6% – 91.1% | 25 |
| generation.citation_recall | 71.1% | 55.7% – 85.1% | 25 |
| generation.citation_validity | 99.2% | 97.7% – 100.0% | 22 |
| correctness.correctness | 76.1% | 61.7% – 88.6% | 24 |
| correctness.fact_coverage | 75.3% | 60.4% – 88.5% | 24 |
| correctness.relevance | 84.9% | 74.5% – 93.5% | 24 |
| abstention.abstention_correct | 86.7% | 73.3% – 96.7% | 30 |
| abstention.false_abstain | 6.7% | 0.0% – 16.7% | 30 |
| abstention.hallucinated_answer | 6.7% | 0.0% – 16.7% | 30 |
| trajectory.iterations | 0.717 | 0.300 – 1.200 | 30 |
| trajectory.terminated_sufficient | 78.3% | 63.3% – 91.7% | 30 |
| trajectory.hit_max_iterations | 21.7% | 8.3% – 36.7% | 30 |
| trajectory.refiner_helped | 12.5% | 0.0% – 37.5% | 4 |
| trajectory.refiner_recall_gain | 0.125 | 0.000 – 0.375 | 4 |
| trajectory.analyzer_decision_correct | 86.7% | 73.3% – 96.7% | 30 |
| trajectory.cost_usd | 0.001 | 0.001 – 0.002 | 30 |
| trajectory.llm_calls | 18.967 | 15.550 – 22.967 | 30 |
| trajectory.had_error | 0.0% | 0.0% – 0.0% | 30 |

## Run-to-run stability (2 repeats per question)

- abstain/answer flips between repeats: 3.3% of questions
- retrieved chunk set differs between repeats: 30.0% of questions
- mean within-question std: correctness 0.037, groundedness 0.017, recall@5 0.029

Differences between two runs smaller than this spread are noise.

## By question type

| type | n | groundedness | citation_precision | citation_recall | correctness | recall@5 | mrr | abstention_correct |
|---|---|---|---|---|---|---|---|---|
| multi-hop | 8 | 92.2% | 79.0% | 81.3% | 61.9% | 68.8% | 0.599 | 100.0% |
| procedural | 9 | 92.6% | 61.2% | 55.4% | 93.1% | 100.0% | 0.870 | 100.0% |
| release-notes | 6 | 97.0% | 98.6% | 92.9% | 82.5% | 83.3% | 0.583 | 83.3% |
| single-hop | 1 | – | – | – | 0.0% | 0.0% | 0.000 | 0.0% |
| unanswerable | 6 | 94.1% | 100.0% | 54.6% | – | – | – | 66.7% |

## Mean node latency (s)

- planner: 1.23
- retriever: 6.27
- analyzer: 2.63
- refiner: 3.74
- synthesizer: 3.04
- verifier: 3.23
