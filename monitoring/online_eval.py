"""Sampled online evaluation of production traces with the same judges used offline.

    python -m monitoring.online_eval --rate 0.25 --hours 24 --max 50

Reference-free metrics only: groundedness, citation precision/recall/validity, answer relevance.
Run it on a schedule (cron / Task Scheduler) or whenever you want the dashboard refreshed.
"""
import argparse
import hashlib
import time

from pydantic import BaseModel

from evals.judges import JUDGE_MODEL, judge
from evals.metrics.generation import evaluate_claims
from observability import store


class Relevance(BaseModel):
    relevance: float   # 0..1


REL_SYSTEM = "Rate how directly the ANSWER addresses the QUESTION (0 = off-topic, 1 = fully on point). Abstentions that honestly say the information is unavailable should be rated on whether they are honest and clear."


def sampled(request_id: str, rate: float) -> bool:
    """Deterministic sampling, so a re-run picks the same traces."""
    return int(hashlib.md5(request_id.encode()).hexdigest(), 16) % 10_000 < rate * 10_000


def score_trace(t: dict) -> dict:
    row = {"request_id": t["request_id"], "ts": time.time(), "judge_model": JUDGE_MODEL, "abstained": int(bool(t["abstained"]))}
    rel = judge(Relevance, REL_SYSTEM, f"QUESTION: {t['question']}\n\nANSWER:\n{t['answer']}")
    row["relevance"] = rel.relevance
    if t["abstained"] or not t["answer"].strip():
        row.update(groundedness=None, citation_precision=None, citation_recall=None, citation_validity=None, n_claims=0, details={})
        return row
    ev = evaluate_claims(t["answer"], t["chunks"])
    row.update(groundedness=ev["groundedness"], citation_precision=ev["citation_precision"],
               citation_recall=ev["citation_recall"], citation_validity=ev["citation_validity"],
               n_claims=ev["n_claims"],
               details={"unsupported": [c["claim"] for c in ev["claims"] if c["needs_citation"] and not c["supporting_chunk_ids"]]})
    return row


def run(rate: float, hours: float, max_n: int, path=None) -> int:
    since = time.time() - hours * 3600
    todo = store.query(
        "SELECT request_id FROM traces WHERE source='app' AND error IS NULL AND ts>=? AND request_id NOT IN "
        "(SELECT request_id FROM online_evals) ORDER BY ts DESC", (since,), path)
    todo = [r["request_id"] for r in todo if sampled(r["request_id"], rate)][:max_n]
    for rid in todo:
        store.save_online_eval(score_trace(store.load_trace(rid, path)), path)
        print("scored", rid)
    print(f"scored {len(todo)} traces")
    return len(todo)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--rate", type=float, default=0.25)
    ap.add_argument("--hours", type=float, default=24 * 7)
    ap.add_argument("--max", type=int, default=50)
    a = ap.parse_args()
    run(a.rate, a.hours, a.max)
