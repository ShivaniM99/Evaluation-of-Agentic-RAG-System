"""Offline evaluation runner.

    python -m evals.run --suite smoke                  # ~8 stratified items, end-to-end
    python -m evals.run --suite full --run-id v2-hybrid
    python -m evals.run --retrieval-only --modes semantic,bm25,hybrid,hybrid_rerank
    python -m evals.run --suite smoke --no-judge       # trajectory + retrieval only (no judge cost)

Writes evals/results/<run_id>.json and .md.
"""
import argparse
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor

from evals import stats
from evals.metrics.retrieval import retrieval_metrics

ROOT = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DATASET = os.path.join(ROOT, "dataset", "golden.jsonl")
RESULTS = os.path.join(ROOT, "results")

AGG_KEYS = [  # (section, metric) averaged over items where defined
    ("retrieval", "recall@5"), ("retrieval", "precision@5"), ("retrieval", "mrr"), ("retrieval", "ndcg@5"),
    ("retrieval", "hit@5"), ("retrieval", "doc_hit@5"), ("retrieval", "context_precision"),
    ("generation", "groundedness"), ("generation", "citation_precision"), ("generation", "citation_recall"),
    ("generation", "citation_validity"),
    ("correctness", "correctness"), ("correctness", "fact_coverage"), ("correctness", "relevance"),
    ("abstention", "abstention_correct"), ("abstention", "false_abstain"), ("abstention", "hallucinated_answer"),
    ("trajectory", "iterations"), ("trajectory", "terminated_sufficient"), ("trajectory", "hit_max_iterations"),
    ("trajectory", "refiner_helped"), ("trajectory", "refiner_recall_gain"),
    ("trajectory", "analyzer_decision_correct"), ("trajectory", "cost_usd"), ("trajectory", "llm_calls"),
    ("trajectory", "had_error"),
]
HEADLINE = [("generation", "groundedness"), ("generation", "citation_precision"), ("generation", "citation_recall"),
            ("correctness", "correctness"), ("retrieval", "recall@5"), ("retrieval", "mrr"),
            ("abstention", "abstention_correct")]


def load_dataset(path=DEFAULT_DATASET) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def pick_suite(items: list[dict], suite: str, limit: int | None) -> list[dict]:
    if suite == "smoke":  # round-robin over types so every behaviour is exercised
        by_type: dict[str, list] = {}
        for it in items:
            by_type.setdefault(it["type"], []).append(it)
        picked, i = [], 0
        while len(picked) < (limit or 8) and any(by_type.values()):
            for t in list(by_type):
                if by_type[t] and len(picked) < (limit or 8):
                    picked.append(by_type[t].pop(0))
            i += 1
        return picked
    return items[:limit] if limit else items


def eval_item(item: dict, index, run_id: str, judge_on: bool, with_draft: bool, max_iter: int) -> dict:
    from observability import store
    from pipeline import run_pipeline_streaming
    from evals.metrics import generation as gen
    from evals.metrics.trajectory import trajectory_metrics

    rec = {"id": item["id"], "type": item["type"], "answerable": item["answerable"], "question": item["question"]}
    gold = set(item.get("gold_chunk_ids", []))
    try:
        rid = None
        for upd in run_pipeline_streaming(item["question"], index, source="eval", run_id=run_id):
            rid = upd["request_id"]
        trace = store.load_trace(rid)
    except Exception as e:
        rec["error"] = f"{type(e).__name__}: {e}"
        return rec
    rec.update(request_id=rid, answer=trace["answer"], abstained_heuristic=bool(trace["abstained"]))
    chunks = trace["chunks"]
    rec["retrieved_ids"] = [c["id"] for c in chunks]
    rec["retrieval"] = retrieval_metrics(rec["retrieved_ids"], gold) if item["answerable"] else {}
    rec["trajectory"] = trajectory_metrics(trace, gold, item["answerable"], max_iter)
    if not judge_on:
        return rec
    try:
        rec["generation"] = gen.evaluate_claims(trace["answer"], chunks) if not trace["abstained"] else \
            {"n_claims": 0, "groundedness": None}
        corr = gen.evaluate_correctness(item["question"], trace["answer"], item["reference_answer"],
                                        item.get("key_facts", []))
        rec["correctness"] = corr if item["answerable"] else {"abstains": corr["abstains"]}
        rec["abstention"] = gen.abstention_score(item["answerable"], corr["abstains"] or trace["abstained"])
        if with_draft and trace.get("draft_answer"):
            d = gen.evaluate_claims(trace["draft_answer"], chunks)
            rec["draft_groundedness"] = d.get("groundedness")
    except Exception as e:
        rec["judge_error"] = f"{type(e).__name__}: {e}"
    return rec


NUM_SECTIONS = ("retrieval", "generation", "correctness", "abstention", "trajectory")


def merge_repeats(recs: list[dict]) -> dict:
    """Collapse N repeated runs of one question into one record: numeric metrics are averaged over repeats,
    plus a `stability` block (run-to-run spread). With a single repeat the record is returned as-is."""
    ok = [r for r in recs if "error" not in r]
    if len(recs) == 1 or not ok:
        return recs[0] if len(recs) == 1 else {**recs[0], "n_repeats": len(recs)}
    out = {k: v for k, v in ok[0].items() if k not in NUM_SECTIONS}
    out["n_repeats"] = len(recs)
    out["n_failed_repeats"] = len(recs) - len(ok)
    for sec in NUM_SECTIONS:
        nums: dict[str, list] = {}
        other: dict = {}
        for r in ok:
            for k, v in (r.get(sec) or {}).items():
                if isinstance(v, (int, float)) and not isinstance(v, bool):
                    nums.setdefault(k, []).append(v)
                else:
                    other.setdefault(k, v)  # claims list, flags, node latency dict: keep the first repeat's
        merged = {**other, **{k: stats.mean(v) for k, v in nums.items()}}
        if sec == "trajectory":
            nodes: dict = {}
            for r in ok:
                for n, secs in (r.get("trajectory") or {}).get("node_latency_s", {}).items():
                    nodes.setdefault(n, []).append(secs)
            merged["node_latency_s"] = {n: stats.mean(v) for n, v in nodes.items()}
        out[sec] = merged
    def spread(sec, key):
        v = [r.get(sec, {}).get(key) for r in ok if isinstance(r.get(sec, {}).get(key), (int, float))]
        return stats.stdev(v) if len(v) > 1 else None
    abst = [bool(r.get("abstained_heuristic")) for r in ok]
    out["stability"] = {
        "correctness_std": spread("correctness", "correctness"),
        "groundedness_std": spread("generation", "groundedness"),
        "recall@5_std": spread("retrieval", "recall@5"),
        "abstain_flip": float(len(set(abst)) > 1),
        "retrieved_set_varies": float(len({tuple(sorted(r.get("retrieved_ids", []))) for r in ok}) > 1),
    }
    out["request_ids"] = [r.get("request_id") for r in ok]
    return out


def _vals(items, section, key):
    return [it.get(section, {}).get(key) for it in items if isinstance(it.get(section, {}).get(key), (int, float))]


def aggregate(items: list[dict]) -> dict:
    ok = [i for i in items if "error" not in i]
    agg = {"n_items": len(items), "n_errors": len(items) - len(ok), "metrics": {}, "by_type": {}}
    for sec, key in AGG_KEYS:
        v = _vals(ok, sec, key)
        if v:
            lo, hi = stats.bootstrap_ci(v)
            agg["metrics"][f"{sec}.{key}"] = {"mean": stats.mean(v), "n": len(v), "ci95": [lo, hi]}
    lat = [i.get("trajectory", {}).get("latency_s") for i in ok]
    agg["latency_s"] = {"p50": stats.percentile(lat, .5), "p95": stats.percentile(lat, .95)}
    agg["total_cost_usd"] = sum(v for v in _vals(ok, "trajectory", "cost_usd"))
    dg = [(i["generation"].get("groundedness"), i.get("draft_groundedness")) for i in ok
          if i.get("generation") and i.get("draft_groundedness") is not None and i["generation"].get("groundedness") is not None]
    if dg:
        agg["verifier_groundedness_lift"] = stats.mean([f - d for f, d in dg])
    st = [i["stability"] for i in ok if i.get("stability")]
    if st:
        agg["stability"] = {
            "n_repeats": max(i.get("n_repeats", 1) for i in ok),
            "abstain_flip_rate": stats.mean([x["abstain_flip"] for x in st]),
            "retrieved_set_varies_rate": stats.mean([x["retrieved_set_varies"] for x in st]),
            "mean_correctness_std": stats.mean([x["correctness_std"] for x in st]),
            "mean_groundedness_std": stats.mean([x["groundedness_std"] for x in st]),
            "mean_recall@5_std": stats.mean([x["recall@5_std"] for x in st]),
        }
    node_lat: dict[str, list] = {}
    for i in ok:
        for n, s in i.get("trajectory", {}).get("node_latency_s", {}).items():
            node_lat.setdefault(n, []).append(s)
    agg["node_latency_mean_s"] = {n: stats.mean(v) for n, v in node_lat.items()}
    for t in sorted({i["type"] for i in ok}):
        sub = [i for i in ok if i["type"] == t]
        agg["by_type"][t] = {"n": len(sub)}
        for sec, key in HEADLINE:
            v = _vals(sub, sec, key)
            if v:
                agg["by_type"][t][f"{sec}.{key}"] = stats.mean(v)
    return agg


def _f(x, pct=True):
    if x is None:
        return "–"
    return f"{x*100:.1f}%" if pct else f"{x:.3f}"


def render_markdown(meta: dict, agg: dict) -> str:
    L = [f"# Eval run `{meta['run_id']}`", "",
         f"- version `{meta.get('version')}` · generator `{meta.get('generator_model')}` · judge `{meta.get('judge_model')}`",
         f"- items {agg['n_items']} ({agg['n_errors']} errors) · pipeline cost ${agg['total_cost_usd']:.3f} · "
         f"judge cost ${agg.get('judge_cost_usd', 0):.3f} ({agg.get('judge_calls', {}).get('calls', 0)} calls, "
         f"{agg.get('judge_calls', {}).get('cached', 0)} cached) · "
         f"latency p50 {_f(agg['latency_s']['p50'], False)}s / p95 {_f(agg['latency_s']['p95'], False)}s", "",
         "## Metrics", "", "| metric | mean | 95% CI | n |", "|---|---|---|---|"]
    pct_free = {"trajectory.iterations", "trajectory.cost_usd", "trajectory.llm_calls", "trajectory.refiner_recall_gain",
                "retrieval.mrr", "retrieval.ndcg@5"}
    for k, v in agg["metrics"].items():
        p = k not in pct_free
        ci = f"{_f(v['ci95'][0], p)} – {_f(v['ci95'][1], p)}" if v["ci95"][0] is not None else "–"
        L.append(f"| {k} | {_f(v['mean'], p)} | {ci} | {v['n']} |")
    if "verifier_groundedness_lift" in agg:
        L += ["", f"Verifier groundedness lift (final − draft): {agg['verifier_groundedness_lift']*100:+.1f} pts"]
    if "stability" in agg:
        sb = agg["stability"]
        L += ["", f"## Run-to-run stability ({sb['n_repeats']} repeats per question)", "",
              f"- abstain/answer flips between repeats: {_f(sb['abstain_flip_rate'])} of questions",
              f"- retrieved chunk set differs between repeats: {_f(sb['retrieved_set_varies_rate'])} of questions",
              f"- mean within-question std: correctness {_f(sb['mean_correctness_std'], False)}, "
              f"groundedness {_f(sb['mean_groundedness_std'], False)}, recall@5 {_f(sb['mean_recall@5_std'], False)}",
              "", "Differences between two runs smaller than this spread are noise."]
    L += ["", "## By question type", "", "| type | n | " + " | ".join(k for _, k in HEADLINE) + " |",
          "|---|---|" + "---|" * len(HEADLINE)]
    for t, row in agg["by_type"].items():
        L.append(f"| {t} | {row['n']} | " + " | ".join(
            _f(row.get(f"{s}.{k}"), k not in ("mrr",)) for s, k in HEADLINE) + " |")
    L += ["", "## Mean node latency (s)", ""] + [f"- {n}: {v:.2f}" for n, v in agg["node_latency_mean_s"].items()]
    return "\n".join(L) + "\n"


def run_retrieval_only(items, modes, k=5):
    from index_loader import load_index
    from evals.retrieval_ablation import rank
    model = load_index()
    out = {}
    for m in modes:
        rows = []
        for it in (i for i in items if i["answerable"]):
            rows.append({"retrieval": retrieval_metrics(rank(model, it["question"], m, k), set(it["gold_chunk_ids"]))})
        out[m] = {key: stats.mean(_vals(rows, "retrieval", key)) for key in
                  ("recall@1", "recall@3", "recall@5", "precision@5", "mrr", "ndcg@5", "doc_hit@5")}
        out[m]["n"] = len(rows)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--suite", choices=["smoke", "full"], default="smoke")
    ap.add_argument("--dataset", default=DEFAULT_DATASET)
    ap.add_argument("--split", choices=["dev", "heldout", "all"], default="dev",
                    help="dev = tuning set (default); heldout = look at only for the final report")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--run-id")
    ap.add_argument("--no-judge", action="store_true")
    ap.add_argument("--with-draft", action="store_true", help="also score the pre-verifier draft (verifier lift)")
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--repeats", type=int, default=1,
                    help="run each question N times; metrics are averaged and run-to-run stability is reported")
    ap.add_argument("--retrieval-only", action="store_true")
    ap.add_argument("--modes", default="semantic,bm25,hybrid,hybrid_rerank")
    a = ap.parse_args()

    os.environ.setdefault("ATLAS_LOG_LEVEL", "WARNING")  # per-span JSON logs drown the report

    items = load_dataset(a.dataset)
    if a.split != "all":
        items = [i for i in items if i.get("split", "dev") == a.split]
    if a.split == "heldout":
        print("NOTE: scoring the held-out set. Report this number once; do not tune against it.")
    items = pick_suite(items, a.suite, a.limit)
    run_id = a.run_id or time.strftime("%Y%m%d-%H%M%S")
    os.makedirs(RESULTS, exist_ok=True)

    if a.retrieval_only:
        res = run_retrieval_only(items, a.modes.split(","))
        print("| mode | R@1 | R@3 | R@5 | P@5 | MRR | nDCG@5 | docHit@5 | n |\n|---|---|---|---|---|---|---|---|---|")
        for m, r in res.items():
            print(f"| {m} | " + " | ".join(_f(r[k], k != 'mrr') for k in
                  ("recall@1", "recall@3", "recall@5", "precision@5", "mrr", "ndcg@5", "doc_hit@5")) + f" | {r['n']} |")
        with open(os.path.join(RESULTS, f"{run_id}-retrieval.json"), "w") as f:
            json.dump(res, f, indent=2)
        return

    from config import MAX_ITERATIONS
    from models import all_models
    from evals.judges import JUDGE_MODEL
    from index_loader import load_index
    from observability.tracing import get_version
    index = load_index()
    fn = lambda it: eval_item(it, index, run_id, not a.no_judge, a.with_draft, MAX_ITERATIONS)
    tasks = [it for it in items for _ in range(a.repeats)]
    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        flat = list(ex.map(fn, tasks))
    results = [merge_repeats(flat[i * a.repeats:(i + 1) * a.repeats]) for i in range(len(items))]
    meta = {"run_id": run_id, "suite": a.suite, "version": get_version(), "generator_model": all_models(),
            "judge_model": None if a.no_judge else JUDGE_MODEL, "dataset": os.path.basename(a.dataset), "repeats": a.repeats, "split": a.split,
            "ts": time.time()}
    agg = aggregate(results)
    from evals.judges import JUDGE_COST
    agg["judge_cost_usd"] = round(JUDGE_COST["usd"], 4)
    agg["judge_calls"] = {k: JUDGE_COST[k] for k in ("calls", "cached", "input_tokens", "output_tokens")}
    with open(os.path.join(RESULTS, f"{run_id}.json"), "w", encoding="utf-8") as f:
        json.dump({"meta": meta, "aggregate": agg, "items": results}, f, indent=2, default=str)
    md = render_markdown(meta, agg)
    with open(os.path.join(RESULTS, f"{run_id}.md"), "w", encoding="utf-8") as f:
        f.write(md)
    print(md)


if __name__ == "__main__":
    main()
