# Eval run `smoke-3-repeats`

- version `b53be8c` · generator `{'planner': 'gpt-4o-mini', 'analyzer': 'gpt-4o-mini', 'refiner': 'gpt-4o-mini', 'synthesizer': 'gpt-4o-mini', 'verifier': 'gpt-4o-mini'}` · judge `gpt-4o`
- items 5 (0 errors) · total cost $0.007 · latency p50 16.932s / p95 22.927s

## Metrics

| metric | mean | 95% CI | n |
|---|---|---|---|
| retrieval.recall@5 | 45.8% | 16.7% – 79.2% | 4 |
| retrieval.precision@5 | 36.8% | 23.6% – 48.6% | 4 |
| retrieval.mrr | 0.625 | 0.333 – 0.917 | 4 |
| retrieval.ndcg@5 | 0.475 | 0.204 – 0.745 | 4 |
| retrieval.hit@5 | 66.7% | 33.3% – 100.0% | 4 |
| retrieval.doc_hit@5 | 66.7% | 33.3% – 100.0% | 4 |
| retrieval.context_precision | 36.8% | 23.6% – 48.6% | 4 |
| generation.groundedness | 72.4% | 50.3% – 94.4% | 5 |
| generation.citation_precision | 65.7% | 34.7% – 93.3% | 5 |
| generation.citation_recall | 62.5% | 30.9% – 94.1% | 5 |
| generation.citation_validity | 96.7% | 90.0% – 100.0% | 5 |
| correctness.correctness | 54.2% | 41.7% – 66.7% | 4 |
| correctness.fact_coverage | 59.7% | 47.2% – 72.2% | 4 |
| correctness.relevance | 87.5% | 75.0% – 100.0% | 4 |
| abstention.abstention_correct | 93.3% | 80.0% – 100.0% | 5 |
| abstention.false_abstain | 6.7% | 0.0% – 20.0% | 5 |
| abstention.hallucinated_answer | 0.0% | 0.0% – 0.0% | 5 |
| trajectory.iterations | 1.067 | 0.000 – 2.267 | 5 |
| trajectory.terminated_sufficient | 73.3% | 40.0% – 100.0% | 5 |
| trajectory.hit_max_iterations | 26.7% | 0.0% – 60.0% | 5 |
| trajectory.refiner_helped | 33.3% | – | 1 |
| trajectory.refiner_recall_gain | 0.167 | – | 1 |
| trajectory.analyzer_decision_correct | 80.0% | 53.3% – 100.0% | 5 |
| trajectory.cost_usd | 0.001 | 0.001 – 0.002 | 5 |
| trajectory.llm_calls | 22.133 | 13.267 – 31.867 | 5 |
| trajectory.had_error | 0.0% | 0.0% – 0.0% | 5 |

## Run-to-run stability (3 repeats per question)

- abstain/answer flips between repeats: 40.0% of questions
- retrieved chunk set differs between repeats: 100.0% of questions
- mean within-question std: correctness 0.217, groundedness 0.029, recall@5 0.144

Differences between two runs smaller than this spread are noise.

## By question type

| type | n | groundedness | citation_precision | citation_recall | correctness | recall@5 | mrr | abstention_correct |
|---|---|---|---|---|---|---|---|---|
| multi-hop | 1 | 100.0% | 100.0% | 70.4% | 66.7% | 50.0% | 1.000 | 100.0% |
| procedural | 1 | 39.8% | 11.9% | 19.8% | 50.0% | 100.0% | 0.833 | 100.0% |
| release-notes | 1 | 72.2% | 66.7% | 22.2% | 66.7% | 16.7% | 0.333 | 100.0% |
| single-hop | 1 | 100.0% | 100.0% | 100.0% | 33.3% | 16.7% | 0.333 | 66.7% |
| unanswerable | 1 | 50.0% | 50.0% | 100.0% | – | – | – | 100.0% |

## Mean node latency (s)

- planner: 1.16
- retriever: 7.30
- analyzer: 2.52
- refiner: 2.46
- synthesizer: 2.08
- verifier: 2.46
