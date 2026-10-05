"""Agent-trajectory metrics from a stored trace (spans + final state)."""
from collections import defaultdict

from evals.metrics.retrieval import recall_at_k


def trajectory_metrics(trace: dict, gold: set[str], answerable: bool, max_iterations: int) -> dict:
    spans = trace["spans"]
    retrievals = [s for s in spans if s["node"] == "retriever"]
    analyzers = [s for s in spans if s["node"] == "analyzer"]
    n_refine = sum(s["node"] == "refiner" for s in spans)

    # recall of gold chunks after each retrieval round -> did refining help?
    recalls = []
    for s in retrievals:
        ids = (s.get("output") or {}).get("chunk_ids", [])
        recalls.append(recall_at_k(ids, gold, len(ids) or 1) if gold else None)
    gain = (recalls[-1] - recalls[0]) if gold and len(recalls) > 1 and None not in (recalls[0], recalls[-1]) else None

    last = (analyzers[-1].get("output") or {}) if analyzers else {}
    final_sufficient = bool(last.get("sufficient"))
    final_recall = recalls[-1] if recalls else None
    # Analyzer decision accuracy: "sufficient" should coincide with having the gold evidence
    # (answerable) and should be False for unanswerable questions.
    if answerable and final_recall is not None:
        analyzer_ok = float(final_sufficient == (final_recall > 0))
    elif not answerable:
        analyzer_ok = float(not final_sufficient)
    else:
        analyzer_ok = None

    per_node = defaultdict(float)
    for s in spans:
        per_node[s["node"]] += s["latency_s"]
    return {
        "iterations": n_refine,
        "hit_max_iterations": float(n_refine >= max_iterations and not final_sufficient),
        "terminated_sufficient": float(final_sufficient),
        "refiner_recall_gain": gain,
        "refiner_helped": (float(gain > 0) if gain is not None and n_refine else None),
        "analyzer_decision_correct": analyzer_ok,
        "node_latency_s": dict(per_node),
        "llm_calls": sum(s.get("llm_calls", 0) for s in spans),
        "prompt_tokens": trace.get("prompt_tokens"),
        "completion_tokens": trace.get("completion_tokens"),
        "cost_usd": trace.get("cost_usd"),
        "latency_s": trace.get("latency_s"),
        "had_error": float(bool(trace.get("error"))),
    }
