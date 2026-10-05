"""Meta-eval of the Verifier node: can it catch claims that are NOT in the evidence?

For each answerable golden item we take the real retrieved chunks and the pipeline's draft answer, inject one
plausible-but-unsupported sentence, run `run_verifier`, and ask a judge whether the injected claim and the
originally-supported content survived.

    python -m evals.verifier_eval --n 20
Reports: catch rate (injected claim removed), false-removal rate (supported content wrongly dropped).
"""
import argparse
import json
import os

from pydantic import BaseModel

from evals.judges import judge
from evals.run import RESULTS, load_dataset


class Fabrication(BaseModel):
    sentence: str


class Survival(BaseModel):
    injected_claim_still_asserted: bool
    original_content_retained: float   # 0..1 share of the original supported claims still present


FAB_SYSTEM = """Write ONE plausible-sounding technical sentence that could appear in a RICOH ProcessDirector answer to the
question, but whose specific facts (a value, property name, version, or step) are NOT stated in the evidence.
It must not contradict the evidence outright; it should be a convincing hallucination. Match the answer's tone."""

SURV_SYSTEM = """You compare an answer BEFORE and AFTER verification. Decide (1) whether the INJECTED CLAIM is still asserted
as fact in the AFTER text (a note that it was not found/unsupported does NOT count as asserting it), and
(2) what share (0..1) of the ORIGINAL answer's substantive content is still present in the AFTER text."""


def run(n: int, max_chunks: int = 5):
    from index_loader import load_index
    from pipeline import run_pipeline_streaming
    from verifier import run_verifier
    from observability import store

    index = load_index()
    items = [i for i in load_dataset() if i["answerable"]][:n]
    rows = []
    for it in items:
        rid = None
        for u in run_pipeline_streaming(it["question"], index, source="eval", run_id="verifier-meta"):
            rid = u["request_id"]
        t = store.load_trace(rid)
        chunks = t["chunks"][:max_chunks]
        if not t["draft_answer"] or not chunks:
            continue
        ev = "\n\n".join(c["text"][:1500] for c in chunks)
        fab = judge(Fabrication, FAB_SYSTEM, f"QUESTION: {it['question']}\n\nEVIDENCE:\n{ev}\n\nANSWER:\n{t['draft_answer']}")
        injected = t["draft_answer"].rstrip() + " " + fab.sentence
        out = run_verifier({"draft_answer": injected, "retrieved_chunks": chunks})
        s = judge(Survival, SURV_SYSTEM, f"INJECTED CLAIM: {fab.sentence}\n\nORIGINAL:\n{t['draft_answer']}\n\nAFTER:\n{out['final_answer']}")
        rows.append({"id": it["id"], "injected": fab.sentence, "caught": not s.injected_claim_still_asserted,
                     "retained": s.original_content_retained})
    n_ = len(rows)
    summary = {"n": n_, "catch_rate": sum(r["caught"] for r in rows) / n_ if n_ else None,
               "false_removal_rate": (1 - sum(r["retained"] for r in rows) / n_) if n_ else None, "rows": rows}
    os.makedirs(RESULTS, exist_ok=True)
    with open(os.path.join(RESULTS, "verifier-meta.json"), "w") as f:
        json.dump(summary, f, indent=2)
    print(f"Verifier meta-eval over {n_} items: catch rate {summary['catch_rate']}, "
          f"false-removal rate {summary['false_removal_rate']}")
    return summary


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=20)
    run(ap.parse_args().n)
