# Eval run `smoke-2-verifier-fix`

- version `b53be8c` · generator `{'planner': 'gpt-4o-mini', 'analyzer': 'gpt-4o-mini', 'refiner': 'gpt-4o-mini', 'synthesizer': 'gpt-4o-mini', 'verifier': 'gpt-4o-mini'}` · judge `gpt-4o`
- items 5 (0 errors) · total cost $0.007 · latency p50 15.947s / p95 24.904s

## Metrics

| metric | mean | 95% CI | n |
|---|---|---|---|
| retrieval.recall@5 | 37.5% | 0.0% – 75.0% | 4 |
| retrieval.precision@5 | 37.5% | 0.0% – 75.0% | 4 |
| retrieval.mrr | 0.500 | 0.000 – 1.000 | 4 |
| retrieval.ndcg@5 | 0.403 | 0.000 – 0.807 | 4 |
| retrieval.hit@5 | 50.0% | 0.0% – 100.0% | 4 |
| retrieval.doc_hit@5 | 50.0% | 0.0% – 100.0% | 4 |
| retrieval.context_precision | 37.5% | 0.0% – 75.0% | 4 |
| generation.groundedness | 80.4% | 60.8% – 100.0% | 3 |
| generation.citation_precision | 36.4% | 0.0% – 100.0% | 3 |
| generation.citation_recall | 8.5% | 0.0% – 13.2% | 3 |
| generation.citation_validity | 100.0% | 100.0% – 100.0% | 3 |
| correctness.correctness | 37.5% | 12.5% – 50.0% | 4 |
| correctness.fact_coverage | 41.7% | 12.5% – 62.5% | 4 |
| correctness.relevance | 87.5% | 62.5% – 100.0% | 4 |
| abstention.abstention_correct | 80.0% | 40.0% – 100.0% | 5 |
| abstention.false_abstain | 20.0% | 0.0% – 60.0% | 5 |
| abstention.hallucinated_answer | 0.0% | 0.0% – 0.0% | 5 |
| trajectory.iterations | 1.200 | 0.000 – 2.400 | 5 |
| trajectory.terminated_sufficient | 60.0% | 20.0% – 100.0% | 5 |
| trajectory.hit_max_iterations | 40.0% | 0.0% – 80.0% | 5 |
| trajectory.refiner_helped | 0.0% | – | 1 |
| trajectory.refiner_recall_gain | 0.000 | – | 1 |
| trajectory.analyzer_decision_correct | 80.0% | 40.0% – 100.0% | 5 |
| trajectory.cost_usd | 0.001 | 0.001 – 0.002 | 5 |
| trajectory.llm_calls | 23.200 | 13.200 – 33.400 | 5 |
| trajectory.had_error | 0.0% | 0.0% – 0.0% | 5 |

Verifier groundedness lift (final − draft): -2.9 pts

## By question type

| type | n | groundedness | citation_precision | citation_recall | correctness | recall@5 | mrr | abstention_correct |
|---|---|---|---|---|---|---|---|---|
| multi-hop | 1 | 100.0% | 100.0% | 11.1% | 50.0% | 50.0% | 1.000 | 100.0% |
| procedural | 1 | 41.2% | 9.1% | 14.3% | 50.0% | 100.0% | 1.000 | 100.0% |
| release-notes | 1 | 100.0% | 0.0% | 0.0% | 50.0% | 0.0% | 0.000 | 100.0% |
| single-hop | 1 | – | – | – | 0.0% | 0.0% | 0.000 | 0.0% |
| unanswerable | 1 | – | – | – | – | – | – | 100.0% |

## Mean node latency (s)

- planner: 1.14
- retriever: 8.07
- analyzer: 2.53
- refiner: 2.86
- synthesizer: 2.04
- verifier: 2.42
