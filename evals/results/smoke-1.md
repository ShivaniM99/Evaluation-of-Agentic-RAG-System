# Eval run `smoke-1`

- version `b53be8c` · generator `{'planner': 'gpt-4o-mini', 'analyzer': 'gpt-4o-mini', 'refiner': 'gpt-4o-mini', 'synthesizer': 'gpt-4o-mini', 'verifier': 'gpt-4o-mini'}` · judge `gpt-4o`
- items 5 (0 errors) · total cost $0.006 · latency p50 17.080s / p95 23.583s

## Metrics

| metric | mean | 95% CI | n |
|---|---|---|---|
| retrieval.recall@5 | 37.5% | 0.0% – 75.0% | 4 |
| retrieval.precision@5 | 33.3% | 0.0% – 75.0% | 4 |
| retrieval.mrr | 0.500 | 0.000 – 1.000 | 4 |
| retrieval.ndcg@5 | 0.403 | 0.000 – 0.807 | 4 |
| retrieval.hit@5 | 50.0% | 0.0% – 100.0% | 4 |
| retrieval.doc_hit@5 | 50.0% | 0.0% – 100.0% | 4 |
| retrieval.context_precision | 33.3% | 0.0% – 75.0% | 4 |
| generation.groundedness | 86.9% | 60.7% – 100.0% | 4 |
| generation.citation_precision | 0.0% | 0.0% – 0.0% | 4 |
| generation.citation_recall | 0.0% | 0.0% – 0.0% | 4 |
| correctness.correctness | 62.5% | 50.0% – 87.5% | 4 |
| correctness.fact_coverage | 70.8% | 54.2% – 91.7% | 4 |
| correctness.relevance | 100.0% | 100.0% – 100.0% | 4 |
| abstention.abstention_correct | 100.0% | 100.0% – 100.0% | 5 |
| abstention.false_abstain | 0.0% | 0.0% – 0.0% | 5 |
| abstention.hallucinated_answer | 0.0% | 0.0% – 0.0% | 5 |
| trajectory.iterations | 0.600 | 0.000 – 1.800 | 5 |
| trajectory.terminated_sufficient | 80.0% | 40.0% – 100.0% | 5 |
| trajectory.hit_max_iterations | 20.0% | 0.0% – 60.0% | 5 |
| trajectory.analyzer_decision_correct | 60.0% | 20.0% – 100.0% | 5 |
| trajectory.cost_usd | 0.001 | 0.001 – 0.002 | 5 |
| trajectory.llm_calls | 18.000 | 13.000 – 27.400 | 5 |
| trajectory.had_error | 0.0% | 0.0% – 0.0% | 5 |

Verifier groundedness lift (final − draft): +0.0 pts

## By question type

| type | n | groundedness | citation_precision | citation_recall | correctness | recall@5 | mrr | abstention_correct |
|---|---|---|---|---|---|---|---|---|
| multi-hop | 1 | 100.0% | 0.0% | 0.0% | 100.0% | 50.0% | 1.000 | 100.0% |
| procedural | 1 | 47.6% | 0.0% | 0.0% | 50.0% | 100.0% | 1.000 | 100.0% |
| release-notes | 1 | 100.0% | 0.0% | 0.0% | 50.0% | 0.0% | 0.000 | 100.0% |
| single-hop | 1 | 100.0% | 0.0% | 0.0% | 50.0% | 0.0% | 0.000 | 100.0% |
| unanswerable | 1 | – | – | – | – | – | – | 100.0% |

## Mean node latency (s)

- planner: 1.66
- retriever: 7.54
- analyzer: 2.87
- synthesizer: 2.13
- verifier: 2.92
- refiner: 3.05
