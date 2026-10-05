"""Generate candidate golden Q/A items from the chunk store (needs OPENAI_API_KEY).

    python -m evals.dataset.build_golden --n 80          # writes evals/dataset/candidates.jsonl
    python -m evals.dataset.review                       # accept / edit / reject into golden.jsonl

Candidates are stratified over doc types and include synthetic *unanswerable* questions
(plausible RPD questions whose answer is deliberately absent from the corpus).
"""
import argparse
import json
import os
import random

from pydantic import BaseModel

from evals.judges import judge

ROOT = os.path.dirname(os.path.abspath(__file__))
CHUNKS = os.path.join(ROOT, "..", "..", "chunks", "chunks.json")


class QA(BaseModel):
    question: str
    reference_answer: str
    key_facts: list[str]
    answerable_from_this_chunk: bool


GEN_SYSTEM = """You write evaluation questions for a RICOH ProcessDirector documentation assistant.
Given ONE documentation chunk, write a realistic question an administrator would ask whose answer is
fully contained in the chunk. Do NOT quote the chunk's title in the question; use natural phrasing.
Return a concise reference answer (2-4 sentences) using only chunk facts, and 1-4 atomic key_facts.
If the chunk has no substantive factual content, set answerable_from_this_chunk=false."""


class Unans(BaseModel):
    questions: list[str]


UNANS_SYSTEM = """Write realistic technical-support questions about RICOH ProcessDirector that the product
user documentation would NOT answer (e.g. hardware sizing, pricing, licensing, competitor comparisons,
third-party OS tuning, roadmap). One sentence each."""

TYPE_FOR_DOC = {"procedure": "procedural", "scenario": "multi-hop", "release-notes": "release-notes"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=80)
    ap.add_argument("--unanswerable", type=int, default=8)
    ap.add_argument("--seed", type=int, default=7)
    a = ap.parse_args()
    rng = random.Random(a.seed)
    chunks = [c for c in json.load(open(CHUNKS, encoding="utf-8"))
              if not c["is_navigational"] and len(c["text"]) > 400]
    by_type = {}
    for c in chunks:
        by_type.setdefault(c["doc_type"], []).append(c)
    quotas = {"procedure": 0.55, "scenario": 0.3, "release-notes": 0.15}
    out = []
    for t, q in quotas.items():
        pool = by_type.get(t, [])
        for c in rng.sample(pool, min(len(pool), round(a.n * q))):
            r = judge(QA, GEN_SYSTEM, f"CHUNK ({c['source_file']} | {c['section_title']}):\n{c['text'][:3500]}")
            if not r.answerable_from_this_chunk:
                continue
            out.append({"id": f"gen-{len(out)+1:03d}", "type": TYPE_FOR_DOC.get(t, "single-hop"),
                        "answerable": True, "question": r.question, "reference_answer": r.reference_answer,
                        "key_facts": r.key_facts, "gold_chunk_ids": [c["chunk_id"]],
                        "source": "synthetic", "reviewed": False})
    u = judge(Unans, UNANS_SYSTEM, f"Write {a.unanswerable} questions.")
    for q in u.questions[:a.unanswerable]:
        out.append({"id": f"gen-{len(out)+1:03d}", "type": "unanswerable", "answerable": False,
                    "question": q, "reference_answer": "Not covered by the documentation; the system should say evidence is insufficient.",
                    "key_facts": [], "gold_chunk_ids": [], "source": "synthetic", "reviewed": False})
    path = os.path.join(ROOT, "candidates.jsonl")
    with open(path, "w", encoding="utf-8") as f:
        for r in out:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"wrote {len(out)} candidates -> {path}\nNext: python -m evals.dataset.review")


if __name__ == "__main__":
    main()
