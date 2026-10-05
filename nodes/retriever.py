# nodes/retriever.py
from index import HybridSearchModel
import faiss
import pickle
import json
import os


def run_retriever(state: dict, index) -> dict:
    all_chunks = []
    seen_ids   = set()

    for sq in state["subquestions"]:
        results = index.search(sq, top_k=5)  # FAISS + BM25 + RRF + entity lookup + LLM rerank

        for chunk in results:
            if chunk["id"] in seen_ids:
                continue
            seen_ids.add(chunk["id"])
            all_chunks.append(chunk)  # already in the right shape, use as-is

    state["retrieved_chunks"] = all_chunks
    return state
