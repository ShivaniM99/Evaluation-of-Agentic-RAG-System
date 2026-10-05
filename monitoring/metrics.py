"""Aggregate KPIs over the trace store (pure functions + thin SQL loaders)."""
import time

from evals.stats import mean, percentile
from observability import store


def load_window(hours: float | None = 24 * 7, source: str = "app", path: str | None = None):
    since = time.time() - hours * 3600 if hours else 0
    traces = store.query("SELECT * FROM traces WHERE source=? AND ts>=? ORDER BY ts", (source, since), path)
    ids = {t["request_id"] for t in traces}
    online = [r for r in store.query("SELECT * FROM online_evals", (), path) if r["request_id"] in ids]
    fb = [r for r in store.query("SELECT * FROM feedback", (), path) if r["request_id"] in ids]
    spans = [r for r in store.query("SELECT * FROM spans", (), path) if r["request_id"] in ids]
    return traces, online, fb, spans


def kpis(traces: list[dict], online: list[dict], feedback: list[dict]) -> dict:
    n = len(traces)
    if not n:
        return {"n_queries": 0}
    ok = [t for t in traces if not t.get("error")]
    rated = [f for f in feedback if f.get("rating")]
    return {
        "n_queries": n,
        "error_rate": 1 - len(ok) / n,
        "abstention_rate": mean([float(bool(t["abstained"])) for t in ok if t["abstained"] is not None]),
        "uncertainty_rate": mean([float(bool(t["uncertainty_flag"])) for t in ok if t["uncertainty_flag"] is not None]),
        "avg_iterations": mean([t["iterations"] for t in ok]),
        "hit_max_iter_rate": mean([float(not t["evidence_sufficient"]) for t in ok if t["evidence_sufficient"] is not None]),
        "latency_p50": percentile([t["latency_s"] for t in ok], .5),
        "latency_p95": percentile([t["latency_s"] for t in ok], .95),
        "avg_cost_usd": mean([t["cost_usd"] for t in ok]),
        "total_cost_usd": sum(t["cost_usd"] or 0 for t in traces),
        "groundedness": mean([r["groundedness"] for r in online]),
        "citation_precision": mean([r["citation_precision"] for r in online]),
        "citation_recall": mean([r["citation_recall"] for r in online]),
        "citation_validity": mean([r["citation_validity"] for r in online]),
        "n_online_scored": len(online),
        "thumbs_up_rate": mean([float(f["rating"] > 0) for f in rated]) if rated else None,
        "wrong_citation_reports": sum(int(f.get("wrong_citation") or 0) for f in feedback),
        "n_feedback": len(feedback),
    }


def daily_series(traces, online, key_fn_traces=None):
    """Bucket by UTC day -> {day: {queries, latency_p50, cost, groundedness}}."""
    day = lambda ts: time.strftime("%Y-%m-%d", time.gmtime(ts))
    out: dict = {}
    for t in traces:
        d = out.setdefault(day(t["ts"]), {"traces": [], "online": []})
        d["traces"].append(t)
    by_id = {t["request_id"]: t for t in traces}
    for r in online:
        t = by_id.get(r["request_id"])
        if t:
            out[day(t["ts"])]["online"].append(r)
    return {d: {"queries": len(v["traces"]),
                "latency_p50": percentile([t["latency_s"] for t in v["traces"]], .5),
                "avg_cost_usd": mean([t["cost_usd"] for t in v["traces"]]),
                "abstention_rate": mean([float(bool(t["abstained"])) for t in v["traces"] if t["abstained"] is not None]),
                "groundedness": mean([r["groundedness"] for r in v["online"]])}
            for d, v in sorted(out.items())}
