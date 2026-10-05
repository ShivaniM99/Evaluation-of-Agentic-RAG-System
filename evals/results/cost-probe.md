# Eval run `cost-probe`

- version `b53be8c` · generator `{'planner': 'gpt-4o-mini', 'analyzer': 'gpt-4o-mini', 'refiner': 'gpt-4o-mini', 'synthesizer': 'gpt-4o-mini', 'verifier': 'gpt-4o-mini'}` · judge `anthropic:claude-sonnet-5-5`
- items 3 (0 errors) · pipeline cost $0.004 · judge cost $0.057 (6 calls, 0 cached) · latency p50 11.505s / p95 28.966s

## Metrics

| metric | mean | 95% CI | n |
|---|---|---|---|
| retrieval.recall@5 | 33.3% | 0.0% – 50.0% | 3 |
| retrieval.precision@5 | 27.8% | 0.0% – 44.4% | 3 |
| retrieval.mrr | 0.667 | 0.000 – 1.000 | 3 |
| retrieval.ndcg@5 | 0.409 | 0.000 – 0.613 | 3 |
| retrieval.hit@5 | 66.7% | 0.0% – 100.0% | 3 |
| retrieval.doc_hit@5 | 66.7% | 0.0% – 100.0% | 3 |
| retrieval.context_precision | 27.8% | 0.0% – 44.4% | 3 |
| generation.groundedness | 83.3% | 50.0% – 100.0% | 3 |
| generation.citation_precision | 58.3% | 33.3% – 100.0% | 3 |
| generation.citation_recall | 80.0% | 60.0% – 100.0% | 3 |
| generation.citation_validity | 83.3% | 66.7% – 100.0% | 3 |
| correctness.correctness | 43.3% | 0.0% – 70.0% | 3 |
| correctness.fact_coverage | 27.8% | 0.0% – 50.0% | 3 |
| correctness.relevance | 75.0% | 30.0% – 100.0% | 3 |
| abstention.abstention_correct | 100.0% | 100.0% – 100.0% | 3 |
| abstention.false_abstain | 0.0% | 0.0% – 0.0% | 3 |
| abstention.hallucinated_answer | 0.0% | 0.0% – 0.0% | 3 |
| trajectory.iterations | 1.000 | 0.000 – 3.000 | 3 |
| trajectory.terminated_sufficient | 66.7% | 0.0% – 100.0% | 3 |
| trajectory.hit_max_iterations | 33.3% | 0.0% – 100.0% | 3 |
| trajectory.refiner_helped | 0.0% | – | 1 |
| trajectory.refiner_recall_gain | 0.000 | – | 1 |
| trajectory.analyzer_decision_correct | 100.0% | 100.0% – 100.0% | 3 |
| trajectory.cost_usd | 0.001 | 0.001 – 0.002 | 3 |
| trajectory.llm_calls | 22.000 | 13.000 – 38.000 | 3 |
| trajectory.had_error | 0.0% | 0.0% – 0.0% | 3 |

## By question type

| type | n | groundedness | citation_precision | citation_recall | correctness | recall@5 | mrr | abstention_correct |
|---|---|---|---|---|---|---|---|---|
| multi-hop | 1 | 100.0% | 100.0% | 100.0% | 70.0% | 50.0% | 1.000 | 100.0% |
| release-notes | 1 | 100.0% | 25.0% | 40.0% | 60.0% | 50.0% | 1.000 | 100.0% |
| single-hop | 1 | 50.0% | 50.0% | 100.0% | 0.0% | 0.0% | 0.000 | 100.0% |

## Mean node latency (s)

- planner: 1.34
- retriever: 9.12
- analyzer: 2.65
- refiner: 2.80
- synthesizer: 1.96
- verifier: 1.81
