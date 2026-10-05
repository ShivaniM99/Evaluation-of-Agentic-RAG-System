# index_loader.py — replace entire file with this
import os
import json
import pickle
from index import HybridSearchModel, load_chunks, load_entity_index
from config import OPENAI_API_KEY

def load_index():
    chunks       = load_chunks("chunks/chunks.json")
    entity_index = load_entity_index("chunks/entity_index.json")
    model        = HybridSearchModel(chunks, entity_index, api_key=OPENAI_API_KEY)

    # Load the pre-built FAISS + BM25 indexes from disk (don't rebuild)
    import faiss
    model.index = faiss.read_index("indexes/faiss_index/index.bin")
    with open("indexes/bm25/bm25_model.pkl", "rb") as f:
        model.bm25 = pickle.load(f)

    print(f"✅ Loaded HybridSearchModel with {len(chunks)} chunks")
    return model