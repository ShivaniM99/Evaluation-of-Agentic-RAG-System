"""Feedback -> golden-set candidates.

    python -m monitoring.feedback          # appends thumbs-down / wrong-citation questions to evals/dataset/candidates.jsonl

Each candidate carries the failing trace id; a human fills in the reference answer in `evals.dataset.review`.
"""
import json
import os

from observability import store

CAND = os.path.join(os.path.dirname(__file__), "..", "evals", "dataset", "candidates.jsonl")


def failure_candidates(path=None) -> list[dict]:
    rows = store.query(
        "SELECT t.request_id, t.question, t.answer, f.rating, f.wrong_citation, f.comment FROM feedback f "
        "JOIN traces t ON t.request_id=f.request_id WHERE f.rating<0 OR f.wrong_citation=1", (), path)
    seen, out = set(), []
    for r in rows:
        if r["question"] in seen:
            continue
        seen.add(r["question"])
        out.append({"id": f"fb-{r['request_id'][:8]}", "type": "single-hop", "answerable": True,
                    "question": r["question"], "reference_answer": "", "key_facts": [], "gold_chunk_ids": [],
                    "source": "user-feedback", "reviewed": False, "failing_trace": r["request_id"],
                    "comment": r["comment"], "wrong_citation": bool(r["wrong_citation"]),
                    "bad_answer": r["answer"]})
    return out


def main():
    cands = failure_candidates()
    existing = set()
    if os.path.exists(CAND):
        existing = {json.loads(l)["id"] for l in open(CAND, encoding="utf-8") if l.strip()}
    new = [c for c in cands if c["id"] not in existing]
    with open(CAND, "a", encoding="utf-8") as f:
        for c in new:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
    print(f"added {len(new)} feedback-derived candidates -> {os.path.normpath(CAND)}")


if __name__ == "__main__":
    main()
