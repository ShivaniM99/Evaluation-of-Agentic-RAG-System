import re
import os
import json
import pickle
import numpy as np
import faiss
from collections import defaultdict
from openai import OpenAI
from rank_bm25 import BM25Okapi
from dotenv import load_dotenv
load_dotenv()
# --- 1. LOAD CHUNKS FROM INGESTION PIPELINE ---
# Replaces DataIngestionPipeline entirely.
# chunks.json and entity_index.json are produced by main_ingest.py

def load_chunks(chunks_path="chunks/chunks.json"):
    with open(chunks_path, "r", encoding="utf-8") as f:
        raw_chunks = json.load(f)

    chunks = [
        {
            "content": c["text"],
            "metadata": {
                "chunk_id":        c["chunk_id"],
                "doc_type":        c["doc_type"],
                "section_title":   c["section_title"],
                "version":         c["version"],
                "source_filename": c["source_file"],
                "navigation_only": c["is_navigational"],
                "page_range":      c["page_range"],
                "breadcrumb":      c["breadcrumb"],
                "entities":        c["entities"],
            }
        }
        for c in raw_chunks
        if not c["is_navigational"]  # navigation-only chunks are not retrieved
    ]

    print(f"Loaded {len(chunks)} retrievable chunks from {chunks_path}")
    return chunks


def load_entity_index(entity_index_path="chunks/entity_index.json"):
    with open(entity_index_path, "r", encoding="utf-8") as f:
        entity_index = json.load(f)
    print(f"Loaded entity index with {len(entity_index)} unique entities")
    return entity_index

RELEVANCE_THRESHOLD = 0.75  # tune this after testing

# --- 2. HYBRID SEARCH MODEL ---
class HybridSearchModel:
    def __init__(self, chunks, entity_index, api_key=os.getenv("OPENAI_API_KEY")):
        self.chunks = chunks
        self.entity_index = entity_index
        self.texts = [c["content"] for c in chunks]
        self.client = OpenAI(api_key=api_key)
        self.model_name = "text-embedding-3-small"

        # chunk_id → list index for fast entity lookup
        self.chunk_id_to_index = {
            c["metadata"]["chunk_id"]: i
            for i, c in enumerate(chunks)
        }

    def get_openai_embeddings(self, text_list, batch_size=100):
        all_embeddings = []
        for i in range(0, len(text_list), batch_size):
            batch = text_list[i: i + batch_size]
            response = self.client.embeddings.create(
                input=batch,
                model=self.model_name
            )
            all_embeddings.extend([data.embedding for data in response.data])
            print(f"  Embedded {min(i + batch_size, len(text_list))}/{len(text_list)} chunks")
        return all_embeddings

    def build_indexes(self):
        os.makedirs("indexes/faiss_index", exist_ok=True)
        os.makedirs("indexes/bm25", exist_ok=True)

        print("Generating OpenAI embeddings...")
        embeddings_list = self.get_openai_embeddings(self.texts)
        self.embeddings = np.array(embeddings_list).astype("float32")

        # Normalize for cosine similarity
        faiss.normalize_L2(self.embeddings)

        # FAISS index — IndexFlatIP for cosine similarity (not L2)
        dim = self.embeddings.shape[1]
        self.index = faiss.IndexFlatIP(dim)
        self.index.add(self.embeddings)
        faiss.write_index(self.index, "indexes/faiss_index/index.bin")

        # BM25 keyword index
        tokenized = [t.split() for t in self.texts]
        self.bm25 = BM25Okapi(tokenized)
        with open("indexes/bm25/bm25_model.pkl", "wb") as f:
            pickle.dump(self.bm25, f)

        # Save chunk metadata separately for lookup
        with open("indexes/faiss_index/chunks_metadata.json", "w") as f:
            json.dump(self.chunks, f, indent=2)

        print(f"Indexes built over {len(self.texts)} chunks")

    def rerank(self, query: str, results: list[dict], threshold: float = 0.3) -> list[dict]:
        """
        Use LLM to rerank and filter retrieved chunks by true relevance.
        Cheap call — just a relevance score per chunk, not full synthesis.
        """
        if not results:
            return []

        scored = []
        for r in results:
            prompt = f"""Query: {query}

    Passage: {r['text'][:500]}

    Does this passage contain information that directly answers the query? 
    Respond with only a number from 0.0 to 1.0 where:
    1.0 = directly answers the query
    0.5 = partially relevant
    0.0 = not relevant at all"""

            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=5
            )

            try:
                score = float(response.choices[0].message.content.strip())
            except:
                score = 0.0

            if score >= threshold:
                r["rerank_score"] = score
                scored.append(r)

        return sorted(scored, key=lambda x: x["rerank_score"], reverse=True)
    
    def search(self, query, top_k=5):
        # Semantic search
        q_embed = np.array(
            self.get_openai_embeddings([query])
        ).astype("float32")
        faiss.normalize_L2(q_embed)  # normalize query too
        D, I = self.index.search(q_embed, top_k * 2)
        semantic_ranks = I[0]

        # Keyword search
        bm_scores = self.bm25.get_scores(query.split())
        keyword_ranks = np.argsort(bm_scores)[::-1][:top_k * 2]

        # Reciprocal Rank Fusion
        rrf_scores = {}
        for rank, idx in enumerate(semantic_ranks):
            rrf_scores[idx] = rrf_scores.get(idx, 0) + 1 / (rank + 1)
        for rank, idx in enumerate(keyword_ranks):
            rrf_scores[idx] = rrf_scores.get(idx, 0) + 1 / (rank + 1)

        ranked = sorted(
            rrf_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )

        # Entity-based expansion
        # If any entity in the query matches the entity index,
        # boost those chunks into results
        entity_chunk_ids = self._entity_lookup(query)
        entity_indices = [
            self.chunk_id_to_index[cid]
            for cid in entity_chunk_ids
            if cid in self.chunk_id_to_index
        ]

        # Add entity matches with a fixed boost score
        existing_indices = {idx for idx, _ in ranked[:top_k]}
        for idx in entity_indices:
            if idx not in existing_indices:
                ranked.append((idx, 0.5))  # boost score

        # Format output
        results = []
        for idx, score in ranked[:top_k]:
            if score < RELEVANCE_THRESHOLD:
                continue  # drop low confidence results
            c = self.chunks[idx]
            results.append({
                "id": c["metadata"]["chunk_id"],
                "text": c["content"],
                "doc": c["metadata"]["source_filename"],
                "section": c["metadata"]["section_title"],
                "page": c["metadata"]["page_range"],
                "breadcrumb": c["metadata"]["breadcrumb"],
                "doc_type": c["metadata"]["doc_type"],
                "version": c["metadata"]["version"],
                "score": round(score, 4),
            })
        results = self.rerank(query, results)
        return results  # empty list if nothing clears the threshold

    def _entity_lookup(self, query: str) -> list[str]:
        """
        Check if any known entity appears in the query.
        Returns chunk_ids of chunks that contain that entity.
        """
        matched_chunk_ids = []
        query_lower = query.lower()
        for entity, chunk_ids in self.entity_index.items():
            if entity.lower() in query_lower:
                matched_chunk_ids.extend(chunk_ids)
        return list(set(matched_chunk_ids))


# --- 3. EXECUTION BLOCK ---
if __name__ == "__main__":
    chunks = load_chunks("chunks/chunks.json")
    entity_index = load_entity_index("chunks/entity_index.json")

    model = HybridSearchModel(chunks, entity_index, api_key=os.getenv("OPENAI_API_KEY"))
    model.build_indexes()

    # Test with an official hackathon question
    query = "How much RAM does the primary server need if I will be doing document-level processing?"
    results = model.search(query)
    print("\n--- Search Results ---")
    print(json.dumps(results, indent=2))