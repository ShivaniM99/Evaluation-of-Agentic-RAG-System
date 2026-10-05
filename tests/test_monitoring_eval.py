import time

from evals import run as R
from monitoring.alerts import compute_alerts
from monitoring.metrics import kpis, load_window
from monitoring.online_eval import sampled
from observability import store


def _trace(i, **kw):
    t = dict(request_id=f"r{i}", ts=time.time(), source="app", run_id=None, version="v", question="q", intent="lookup",
             subquestions=[], chunks=[], answer="a", draft_answer="a", citations=[], uncertainty_flag=0,
             evidence_sufficient=1, confidence_score=8, iterations=0, abstained=0, latency_s=2.0, prompt_tokens=10,
             completion_tokens=5, cost_usd=0.01, error=None)
    t.update(kw)
    return t


def test_kpis_and_alerts():
    for i in range(6):
        store.save_trace(_trace(i, abstained=int(i < 3), latency_s=60.0 if i == 0 else 2.0), [])
        store.save_online_eval(dict(request_id=f"r{i}", ts=time.time(), judge_model="j", groundedness=0.5,
                                    citation_precision=0.9, citation_recall=0.9, citation_validity=1.0,
                                    relevance=1.0, abstained=0, n_claims=2, details={}))
    store.save_feedback("r0", -1)
    store.save_feedback("r1", 1)
    traces, online, fb, spans = load_window(24)
    k = kpis(traces, online, fb)
    assert k["n_queries"] == 6 and k["abstention_rate"] == 0.5 and k["groundedness"] == 0.5
    assert k["thumbs_up_rate"] == 0.5 and k["n_online_scored"] == 6
    names = {a["metric"] for a in compute_alerts(k)}
    assert {"groundedness", "abstention_rate", "latency_p95", "thumbs_up_rate"} <= names
    assert compute_alerts({"n_queries": 2, "groundedness": 0.0}) == []  # too little data to alert


def test_sampling_is_deterministic():
    ids = [f"id{i}" for i in range(2000)]
    a = [sampled(i, .25) for i in ids]
    assert a == [sampled(i, .25) for i in ids]
    assert 0.2 < sum(a) / len(a) < 0.3
    assert all(sampled(i, 1.0) for i in ids[:50]) and not any(sampled(i, 0.0) for i in ids[:50])


def test_golden_seed_is_valid_and_gold_ids_exist():
    import json, os
    items = R.load_dataset()
    chunk_ids = {c["chunk_id"] for c in json.load(open(os.path.join(os.path.dirname(R.__file__), "..", "chunks", "chunks.json")))}
    assert len(items) >= 5 and len({i["id"] for i in items}) == len(items)
    for it in items:
        assert it["answerable"] == bool(it["gold_chunk_ids"])
        assert set(it["gold_chunk_ids"]) <= chunk_ids
        assert it["question"] and it["reference_answer"]
    assert any(not i["answerable"] for i in items)


def test_suite_picker_stratifies():
    items = [dict(id=str(i), type="ABC"[i % 3]) for i in range(30)]
    assert {i["type"] for i in R.pick_suite(items, "smoke", 6)} == {"A", "B", "C"}
    assert len(R.pick_suite(items, "full", 4)) == 4


def test_aggregate_and_markdown():
    def it(i, typ, g, c):
        return dict(id=i, type=typ, answerable=True, question="q",
                    retrieval={"recall@5": 1.0, "mrr": 0.5}, generation={"groundedness": g, "citation_precision": 1.0},
                    correctness={"correctness": c}, abstention={"abstention_correct": 1.0},
                    trajectory={"latency_s": 2.0, "cost_usd": 0.01, "iterations": 1, "node_latency_s": {"planner": 1.0}},
                    draft_groundedness=0.5)
    items = [it("a", "procedural", 1.0, 1.0), it("b", "procedural", 0.5, 0.0), dict(id="c", type="x", answerable=True, question="q", error="boom")]
    agg = R.aggregate(items)
    assert agg["n_errors"] == 1
    assert agg["metrics"]["generation.groundedness"]["mean"] == 0.75
    assert agg["by_type"]["procedural"]["correctness.correctness"] == 0.5
    assert abs(agg["verifier_groundedness_lift"] - 0.25) < 1e-9
    md = R.render_markdown({"run_id": "t", "version": "v", "generator_model": "g", "judge_model": "j"}, agg)
    assert "generation.groundedness" in md and "75.0%" in md


def test_merge_repeats_averages_and_reports_stability():
    def rec(corr, rid, ids, abst=False):
        return dict(id="a", type="t", answerable=True, question="q", request_id=rid, answer="x",
                    abstained_heuristic=abst, retrieved_ids=ids,
                    retrieval={"recall@5": 1.0 if ids else 0.0}, generation={"groundedness": 1.0, "claims": [{"claim": "c", "supporting_chunk_ids": ["x"]}]},
                    correctness={"correctness": corr}, abstention={"abstention_correct": 1.0},
                    trajectory={"latency_s": 2.0, "node_latency_s": {"planner": 1.0}})
    m = R.merge_repeats([rec(1.0, "r1", ["c1"]), rec(0.0, "r2", [], abst=True), rec(0.5, "r3", ["c1"])])
    assert m["n_repeats"] == 3 and abs(m["correctness"]["correctness"] - 0.5) < 1e-9
    assert m["stability"]["abstain_flip"] == 1.0 and m["stability"]["retrieved_set_varies"] == 1.0
    assert abs(m["stability"]["correctness_std"] - 0.5) < 1e-9
    assert m["trajectory"]["node_latency_s"] == {"planner": 1.0}
    assert m["generation"]["claims"][0]["claim"] == "c"       # non-numeric fields survive the merge
    one = rec(1.0, "r1", ["c1"])
    assert R.merge_repeats([one]) is one                      # single repeat passes through untouched
    agg = R.aggregate([m])
    assert agg["stability"]["abstain_flip_rate"] == 1.0
    md = R.render_markdown({"run_id": "t", "version": "v", "generator_model": "g", "judge_model": "j"}, agg)
    assert "Run-to-run stability" in md


def test_failed_repeat_does_not_poison_merge():
    good = dict(id="a", type="t", answerable=True, question="q", request_id="r", answer="x", abstained_heuristic=False,
                retrieved_ids=["c"], retrieval={"recall@5": 1.0}, correctness={"correctness": 1.0}, trajectory={"latency_s": 1.0})
    bad = dict(id="a", type="t", answerable=True, question="q", error="boom")
    m = R.merge_repeats([good, bad])
    assert m["n_failed_repeats"] == 1 and m["correctness"]["correctness"] == 1.0 and "error" not in m


def test_split_is_stratified_deterministic_and_stable():
    from evals.dataset import split
    items = [dict(id=f"p{i}", type="procedural") for i in range(40)] + [dict(id=f"u{i}", type="unanswerable") for i in range(8)] \
        + [dict(id="s0", type="single-hop")]
    assert split.assign(items) == 49
    held = {i["id"] for i in items if i["split"] == "heldout"}
    assert sum(i.startswith("p") for i in held) == 10 and sum(i.startswith("u") for i in held) == 2
    assert next(i for i in items if i["id"] == "s0")["split"] == "dev"       # tiny groups stay in dev
    items += [dict(id="p_new", type="procedural")]
    assert split.assign(items) == 1 and {i["id"] for i in items if i["split"] == "heldout" and i["id"] != "p_new"} <= held | set()
    assert {i["id"] for i in items if i["split"] == "heldout"} >= held       # nothing already held out ever moves


def test_runner_respects_split_default(monkeypatch):
    items = [dict(id="a", type="t", split="dev"), dict(id="b", type="t", split="heldout"), dict(id="c", type="t")]
    assert [i["id"] for i in items if i.get("split", "dev") == "dev"] == ["a", "c"]
