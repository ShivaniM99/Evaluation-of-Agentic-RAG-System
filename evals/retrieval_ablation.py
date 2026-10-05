"""Retriever ablations on the raw question (no planner): semantic / bm25 / hybrid (RRF) / hybrid+rerank."""
import faiss
import numpy as np

MODES = ("semantic", "bm25", "hybrid", "hybrid_rerank")


def _rank_ids(model, idxs, k):
    return [model.chunks[i]["metadata"]["chunk_id"] for i in idxs[:k]]


def rank(model, query: str, mode: str, k: int = 5) -> list[str]:
    if mode == "semantic":
        q = np.array(model.get_openai_embeddings([query])).astype("float32")
        faiss.normalize_L2(q)
        _, I = model.index.search(q, k)
        return _rank_ids(model, I[0], k)
    if mode == "bm25":
        scores = model.bm25.get_scores(query.split())
        return _rank_ids(model, list(np.argsort(scores)[::-1]), k)
    if mode in ("hybrid", "hybrid_rerank"):
        orig = model.rerank
        if mode == "hybrid":  # RRF + entity boost + threshold, skip the LLM reranker
            model.rerank = lambda q, results, threshold=0.3: results
        try:
            return [r["id"] for r in model.search(query, top_k=k)]
        finally:
            model.rerank = orig
    raise ValueError(f"unknown mode {mode}")
