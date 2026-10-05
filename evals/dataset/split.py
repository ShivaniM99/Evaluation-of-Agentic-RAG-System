"""Assign each golden item to `dev` (tune on this) or `heldout` (look at once, at the end).

    python -m evals.dataset.split            # idempotent: only items without a `split` get one

Stratified by question type, deterministic (hash of the id), ~25% held out. Existing assignments never change,
so the held-out set stays untouched as the dataset grows.
"""
import hashlib
import json
import math
import os
from collections import defaultdict

GOLD = os.path.join(os.path.dirname(os.path.abspath(__file__)), "golden.jsonl")
HELDOUT_FRACTION = 0.25


def _h(i: str) -> str:
    return hashlib.sha1(i.encode()).hexdigest()


def assign(items: list[dict]) -> int:
    by_type = defaultdict(list)
    for it in items:
        by_type[it["type"]].append(it)
    changed = 0
    for t, group in by_type.items():
        have_held = sum(g.get("split") == "heldout" for g in group)
        want = math.floor(len(group) * HELDOUT_FRACTION + 0.5) if len(group) >= 4 else 0
        todo = sorted((g for g in group if "split" not in g), key=lambda g: _h(g["id"]))
        for g in todo:
            if have_held < want:
                g["split"], have_held = "heldout", have_held + 1
            else:
                g["split"] = "dev"
            changed += 1
    return changed


def main():
    items = [json.loads(l) for l in open(GOLD, encoding="utf-8") if l.strip()]
    n = assign(items)
    with open(GOLD, "w", encoding="utf-8") as f:
        for it in items:
            f.write(json.dumps(it, ensure_ascii=False) + "\n")
    c = defaultdict(lambda: defaultdict(int))
    for it in items:
        c[it["type"]][it["split"]] += 1
    print(f"assigned {n} new items")
    for t, d in c.items():
        print(f"  {t:14s} dev={d['dev']:3d} heldout={d['heldout']:3d}")


if __name__ == "__main__":
    main()
