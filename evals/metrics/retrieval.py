"""Rank-based retrieval metrics against gold chunk ids. Pure functions, no API calls."""
import math


def recall_at_k(ranked: list[str], gold: set[str], k: int) -> float | None:
    if not gold:
        return None
    return len(set(ranked[:k]) & gold) / len(gold)


def precision_at_k(ranked: list[str], gold: set[str], k: int) -> float | None:
    top = ranked[:k]
    if not gold:
        return None
    return (len([c for c in top if c in gold]) / len(top)) if top else 0.0


def hit_at_k(ranked: list[str], gold: set[str], k: int) -> float | None:
    if not gold:
        return None
    return float(bool(set(ranked[:k]) & gold))


def mrr(ranked: list[str], gold: set[str]) -> float | None:
    if not gold:
        return None
    for i, c in enumerate(ranked, 1):
        if c in gold:
            return 1.0 / i
    return 0.0


def ndcg_at_k(ranked: list[str], gold: set[str], k: int) -> float | None:
    if not gold:
        return None
    dcg = sum(1.0 / math.log2(i + 2) for i, c in enumerate(ranked[:k]) if c in gold)
    ideal = sum(1.0 / math.log2(i + 2) for i in range(min(len(gold), k)))
    return dcg / ideal if ideal else 0.0


def doc_of(chunk_id: str) -> str:
    return chunk_id.rsplit("_chunk_", 1)[0]


def retrieval_metrics(ranked: list[str], gold: set[str], ks=(1, 3, 5)) -> dict:
    out = {"mrr": mrr(ranked, gold), "ndcg@5": ndcg_at_k(ranked, gold, 5)}
    for k in ks:
        out[f"recall@{k}"] = recall_at_k(ranked, gold, k)
        out[f"precision@{k}"] = precision_at_k(ranked, gold, k)
        out[f"hit@{k}"] = hit_at_k(ranked, gold, k)
    gold_docs = {doc_of(g) for g in gold}
    out["doc_hit@5"] = float(bool({doc_of(c) for c in ranked[:5]} & gold_docs)) if gold else None
    # context precision: share of retrieved chunks that are relevant (any gold doc)
    out["context_precision"] = (
        sum(doc_of(c) in gold_docs for c in ranked) / len(ranked) if ranked and gold else (0.0 if gold else None))
    return out
