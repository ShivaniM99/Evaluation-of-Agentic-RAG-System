"""Judge calibration against human labels.

    python -m evals.calibrate export --run results/<run>.json --n 25     # writes evals/results/calibration.csv
    # open the CSV, fill the human_* columns with 1/0 (supported? / correct?), save
    python -m evals.calibrate score                                     # prints agreement + Cohen's kappa

Unit of labelling: one atomic claim -> "is it supported by the retrieved evidence?" (judge: supporting_chunk_ids non-empty),
plus one row per answer -> "is the answer correct vs. the reference?" (judge: correctness >= 0.5).
"""
import argparse
import csv
import json
import os
import random

from evals.run import RESULTS
from evals.stats import cohens_kappa

CSV_PATH = os.path.join(RESULTS, "calibration.csv")
FIELDS = ["kind", "item_id", "text", "context_or_reference", "judge_label", "human_label"]


def export(run_path: str, n: int, seed: int = 3):
    data = json.load(open(run_path, encoding="utf-8"))
    from observability import store
    rows = []
    for it in data["items"]:
        if "request_id" not in it:
            continue
        t = store.load_trace(it["request_id"])
        ctx = "\n---\n".join(f"[{c['id']}] {c['text'][:600]}" for c in (t["chunks"] if t else []))
        for cl in it.get("generation", {}).get("claims", []):
            if cl["needs_citation"]:
                rows.append(["claim", it["id"], cl["claim"], ctx, int(bool(cl["supporting_chunk_ids"])), ""])
        if it.get("correctness", {}).get("correctness") is not None:
            rows.append(["answer", it["id"], it.get("answer", ""), it["question"], int(it["correctness"]["correctness"] >= 0.5), ""])
    random.Random(seed).shuffle(rows)
    rows = rows[:n]
    os.makedirs(RESULTS, exist_ok=True)
    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(FIELDS)
        w.writerows(rows)
    print(f"wrote {len(rows)} rows -> {CSV_PATH}. Fill human_label with 1/0 then run: python -m evals.calibrate score")


def score():
    rows = [r for r in csv.DictReader(open(CSV_PATH, encoding="utf-8")) if r["human_label"].strip() in ("0", "1")]
    if not rows:
        print("No human labels found.")
        return
    for kind in ("claim", "answer", None):
        sub = [r for r in rows if kind is None or r["kind"] == kind]
        if not sub:
            continue
        j = [int(r["judge_label"]) for r in sub]
        h = [int(r["human_label"]) for r in sub]
        agree = sum(a == b for a, b in zip(j, h)) / len(sub)
        print(f"{kind or 'all':7s} n={len(sub):3d} agreement={agree:.2%} kappa={cohens_kappa(j, h):.3f}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["export", "score"])
    ap.add_argument("--run")
    ap.add_argument("--n", type=int, default=25)
    a = ap.parse_args()
    export(a.run, a.n) if a.cmd == "export" else score()
