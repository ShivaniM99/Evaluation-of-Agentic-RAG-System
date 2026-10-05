"""Auto-validate candidate golden items with a second model family (no human review needed).

    python -m evals.dataset.validate                       # validator: anthropic:claude-sonnet-5-5
    VALIDATOR_MODEL=anthropic:claude-... python -m evals.dataset.validate

For every candidate in candidates.jsonl:
  answerable   -> Claude sees ONLY the gold chunk and must confirm: the question is answerable from it, every
                  reference key fact is stated in it, and the question is self-contained and unambiguous.
  unanswerable -> Claude sees the BM25 top-5 chunks for the question and must confirm none of them answers it.
Plus duplicate removal. Survivors are appended to golden.jsonl with reviewed="auto"; rejects go to
rejected.jsonl with the validator's reasons, so you can audit what was dropped.
"""
import argparse
import json
import os
import re

from pydantic import BaseModel

from evals.judges import judge

ROOT = os.path.dirname(os.path.abspath(__file__))
CAND, GOLD, REJ = (os.path.join(ROOT, f) for f in ("candidates.jsonl", "golden.jsonl", "rejected.jsonl"))
CHUNKS = os.path.join(ROOT, "..", "..", "chunks", "chunks.json")
VALIDATOR = os.getenv("VALIDATOR_MODEL", "anthropic:claude-sonnet-5-5")


class AnswerableCheck(BaseModel):
    answerable_from_chunk: bool        # the question can be answered using ONLY this chunk
    key_facts_supported: list[bool]    # one per key fact, in order: stated or clearly entailed by the chunk
    reference_has_no_extra_claims: bool  # the reference answer adds nothing beyond the chunk
    self_contained: bool               # makes sense with no document in front of the asker (no "this procedure")
    unambiguous: bool                  # a single reasonable interpretation
    problems: str


ANS_SYSTEM = """You validate evaluation items for a documentation Q&A system. You see ONE documentation chunk and a
candidate question with a reference answer and key facts. Judge strictly using only the chunk text.
- answerable_from_chunk: can the question be fully answered from this chunk alone?
- key_facts_supported: for each key fact in order, true only if the chunk states or clearly entails it.
- reference_has_no_extra_claims: false if the reference answer asserts anything the chunk does not support.
- self_contained: false if the question depends on context outside itself (e.g. "in this procedure", "the above").
- unambiguous: false if it could reasonably mean different things.
List any problems briefly in `problems`."""


class UnansweredCheck(BaseModel):
    any_chunk_answers: bool            # at least one of the provided chunks answers the question
    realistic: bool                    # a plausible support question for this product
    problems: str


UNANS_SYSTEM = """You validate 'unanswerable' evaluation questions. The system's documentation should NOT contain the
answer. You see the 5 most similar documentation chunks. Set any_chunk_answers=true if any of them answers (even partly)
the question. realistic=false if the question is nonsensical or not about this product."""


def norm(q: str) -> str:
    return re.sub(r"[^a-z0-9 ]", "", q.lower()).strip()


def jaccard(a: str, b: str) -> float:
    x, y = set(norm(a).split()), set(norm(b).split())
    return len(x & y) / len(x | y) if x | y else 0.0


def validate_answerable(c: dict, chunks: dict) -> tuple[bool, str]:
    gold = [chunks[g] for g in c["gold_chunk_ids"] if g in chunks]
    if not gold:
        return False, "gold chunk missing"
    text = "\n\n".join(g["text"][:4000] for g in gold)
    facts = c.get("key_facts") or []
    r = judge(AnswerableCheck, ANS_SYSTEM,
              f"CHUNK:\n{text}\n\nQUESTION: {c['question']}\nREFERENCE ANSWER: {c['reference_answer']}\n"
              "KEY FACTS:\n" + "\n".join(f"{i+1}. {f}" for i, f in enumerate(facts)), model=VALIDATOR)
    ok = (r.answerable_from_chunk and r.reference_has_no_extra_claims and r.self_contained and r.unambiguous
          and bool(facts) and all(r.key_facts_supported[:len(facts)]) and len(r.key_facts_supported) >= len(facts))
    return ok, r.problems


def validate_unanswerable(c: dict, bm25, chunk_list: list[dict]) -> tuple[bool, str]:
    import numpy as np
    scores = bm25.get_scores(c["question"].split())
    top = [chunk_list[i] for i in np.argsort(scores)[::-1][:5]]
    ctx = "\n\n".join(f"[{t['chunk_id']}]\n{t['text'][:1500]}" for t in top)
    r = judge(UnansweredCheck, UNANS_SYSTEM, f"QUESTION: {c['question']}\n\nCHUNKS:\n{ctx}", model=VALIDATOR)
    return (not r.any_chunk_answers) and r.realistic, r.problems


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    all_chunks = json.load(open(CHUNKS, encoding="utf-8"))
    chunks = {c["chunk_id"]: c for c in all_chunks}
    gold = [json.loads(l) for l in open(GOLD, encoding="utf-8")] if os.path.exists(GOLD) else []
    have_ids = {g["id"] for g in gold}
    seen_q = [g["question"] for g in gold]
    cands = [json.loads(l) for l in open(CAND, encoding="utf-8") if l.strip()]

    bm25 = retr_chunks = None
    if any(not c["answerable"] for c in cands):
        import pickle
        bm25 = pickle.load(open(os.path.join(ROOT, "..", "..", "indexes", "bm25", "bm25_model.pkl"), "rb"))
        retr_chunks = [c for c in all_chunks if not c["is_navigational"]]

    accepted, rejected = [], []
    for c in cands:
        if c["id"] in have_ids:
            continue
        if any(jaccard(c["question"], q) > 0.7 for q in seen_q):
            rejected.append({**c, "reject_reason": "near-duplicate question"})
            continue
        try:
            ok, why = (validate_answerable(c, chunks) if c["answerable"]
                       else validate_unanswerable(c, bm25, retr_chunks))
        except Exception as e:
            ok, why = False, f"validator error: {type(e).__name__}: {e}"
        if ok:
            c["reviewed"] = "auto"
            c["validator"] = VALIDATOR
            accepted.append(c)
            seen_q.append(c["question"])
        else:
            rejected.append({**c, "reject_reason": why})
        print(("ACCEPT " if ok else "REJECT ") + c["id"], "|", c["question"][:80], "" if ok else f"| {why[:100]}")

    print(f"\naccepted {len(accepted)} / rejected {len(rejected)}")
    if a.dry_run:
        return
    with open(GOLD, "a", encoding="utf-8") as f:
        for c in accepted:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
    with open(REJ, "w", encoding="utf-8") as f:
        for c in rejected:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
    print(f"wrote golden.jsonl (+{len(accepted)}), rejected.jsonl ({len(rejected)})")


if __name__ == "__main__":
    main()
