"""Interactive review of candidate items: [a]ccept, [e]dit, [r]eject, [s]kip, [q]uit.

Accepted items are appended to golden.jsonl (reviewed=true). Already-present ids are skipped.
Multi-hop upgrades: when editing, you can add extra gold chunk ids (comma separated).
"""
import json
import os

ROOT = os.path.dirname(os.path.abspath(__file__))
CAND, GOLD = os.path.join(ROOT, "candidates.jsonl"), os.path.join(ROOT, "golden.jsonl")
CHUNKS = os.path.join(ROOT, "..", "..", "chunks", "chunks.json")


def load(p):
    return [json.loads(l) for l in open(p, encoding="utf-8")] if os.path.exists(p) else []


def main():
    chunks = {c["chunk_id"]: c for c in json.load(open(CHUNKS, encoding="utf-8"))}
    gold = load(GOLD)
    have = {g["id"] for g in gold}
    todo = [c for c in load(CAND) if c["id"] not in have]
    print(f"{len(todo)} candidates to review, {len(gold)} items already in golden.jsonl")
    for c in todo:
        print("\n" + "=" * 80)
        print(f"{c['id']}  [{c['type']}]  answerable={c['answerable']}")
        print("Q:", c["question"])
        print("A:", c["reference_answer"])
        print("facts:", c["key_facts"])
        for gid in c["gold_chunk_ids"]:
            ch = chunks.get(gid)
            print(f"--- gold {gid}: {ch['text'][:500] if ch else 'MISSING'}")
        act = input("[a]ccept [e]dit [r]eject [s]kip [q]uit > ").strip().lower()
        if act == "q":
            break
        if act == "e":
            c["question"] = input(f"question [{c['question']}]: ") or c["question"]
            c["reference_answer"] = input("reference answer (enter keeps): ") or c["reference_answer"]
            facts = input("key facts separated by ';' (enter keeps): ")
            if facts:
                c["key_facts"] = [f.strip() for f in facts.split(";") if f.strip()]
            extra = input("extra gold chunk ids, comma separated: ")
            c["gold_chunk_ids"] += [x.strip() for x in extra.split(",") if x.strip() in chunks]
            act = "a"
        if act == "a":
            c["reviewed"] = True
            with open(GOLD, "a", encoding="utf-8") as f:
                f.write(json.dumps(c, ensure_ascii=False) + "\n")
            print("accepted")


if __name__ == "__main__":
    main()
