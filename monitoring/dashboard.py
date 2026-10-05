"""Streamlit monitoring dashboard.   streamlit run monitoring/dashboard.py   (or the Monitoring page in the app)"""
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import streamlit as st

from monitoring.alerts import compute_alerts
from monitoring.metrics import daily_series, kpis, load_window
from observability import store


def _pct(x):
    return "–" if x is None else f"{x*100:.1f}%"


def _num(x, fmt="{:.2f}"):
    return "–" if x is None else fmt.format(x)


def render():
    st.title("ATLAS Monitoring")
    c1, c2 = st.columns([1, 1])
    hours = {"Last 24h": 24, "Last 7 days": 24 * 7, "Last 30 days": 24 * 30, "All time": None}[
        c1.selectbox("Window", ["Last 24h", "Last 7 days", "Last 30 days", "All time"], index=1)]
    source = c2.selectbox("Source", ["app", "eval"], index=0)
    traces, online, fb, spans = load_window(hours, source)
    k = kpis(traces, online, fb)
    if not k["n_queries"]:
        st.info("No traces yet. Ask ATLAS a question in the main app, then come back.")
        return

    for a in compute_alerts(k):
        (st.error if a["severity"] == "critical" else st.warning)(
            f"**{a['message']}** — {a['metric']} = {a['value']:.3g} (threshold {a['threshold']:.3g})")

    st.subheader("Quality")
    q = st.columns(5)
    q[0].metric("Groundedness", _pct(k["groundedness"]), help="Online-scored sample; claims supported by retrieved evidence")
    q[1].metric("Citation precision", _pct(k["citation_precision"]))
    q[2].metric("Citation recall", _pct(k["citation_recall"]))
    q[3].metric("Fabricated-citation check", _pct(k["citation_validity"]), help="Citations that resolve to a retrieved chunk")
    q[4].metric("Thumbs-up", _pct(k["thumbs_up_rate"]), help=f"{k['n_feedback']} feedback events")
    st.caption(f"{k['n_online_scored']} of {k['n_queries']} queries scored online "
               "(`python -m monitoring.online_eval`).")

    st.subheader("Agent behaviour")
    b = st.columns(5)
    b[0].metric("Queries", k["n_queries"])
    b[1].metric("Abstention rate", _pct(k["abstention_rate"]))
    b[2].metric("Uncertainty flagged", _pct(k["uncertainty_rate"]))
    b[3].metric("Avg refiner loops", _num(k["avg_iterations"]))
    b[4].metric("Evidence never sufficient", _pct(k["hit_max_iter_rate"]))

    st.subheader("Latency & cost")
    p = st.columns(5)
    p[0].metric("p50 latency", _num(k["latency_p50"], "{:.1f}s"))
    p[1].metric("p95 latency", _num(k["latency_p95"], "{:.1f}s"))
    p[2].metric("Avg cost / query", _num(k["avg_cost_usd"], "${:.4f}"))
    p[3].metric("Total cost", _num(k["total_cost_usd"], "${:.3f}"))
    p[4].metric("Error rate", _pct(k["error_rate"]))

    ds = pd.DataFrame(daily_series(traces, online)).T
    if len(ds) > 1:
        t1, t2, t3 = st.tabs(["Groundedness / abstention", "Latency", "Cost & volume"])
        t1.line_chart(ds[["groundedness", "abstention_rate"]].astype(float))
        t2.line_chart(ds[["latency_p50"]].astype(float))
        t3.bar_chart(ds[["queries"]].astype(float))
        t3.line_chart(ds[["avg_cost_usd"]].astype(float))

    st.subheader("Where does time and money go?")
    if spans:
        sp = pd.DataFrame(spans).groupby("node").agg(
            mean_latency_s=("latency_s", "mean"), mean_cost_usd=("cost_usd", "mean"),
            mean_tokens=("prompt_tokens", "mean"), calls=("id", "count")).round(4)
        st.dataframe(sp, use_container_width=True)

    st.subheader("Retrieval score distribution")
    scores = []
    for t in traces:
        for c in json.loads(t["chunks"] or "[]"):
            if c.get("rerank_score") is not None:
                scores.append(c["rerank_score"])
    if scores:
        st.bar_chart(pd.Series(scores).round(1).value_counts().sort_index())

    st.subheader("Needs attention")
    tab_a, tab_b, tab_c = st.tabs(["Unsupported claims", "User-flagged", "Slowest / costliest"])
    bad = [(r, json.loads(r["details"] or "{}").get("unsupported", [])) for r in online]
    bad = [(r, u) for r, u in bad if u]
    by_id = {t["request_id"]: t for t in traces}
    for r, u in bad[:20]:
        with tab_a.expander(by_id[r["request_id"]]["question"][:100]):
            st.write("Unsupported:", u)
            st.caption(f"trace {r['request_id']}")
    flagged = {f["request_id"]: f for f in fb if (f["rating"] or 0) < 0 or f["wrong_citation"]}
    for rid, f in list(flagged.items())[:20]:
        t = by_id.get(rid)
        if t:
            with tab_b.expander(("👎 " if (f["rating"] or 0) < 0 else "") + ("❌ citation " if f["wrong_citation"] else "") + t["question"][:90]):
                st.write(t["answer"])
                st.caption(f["comment"] or "")
    top = sorted(traces, key=lambda t: t["latency_s"] or 0, reverse=True)[:10]
    tab_c.dataframe(pd.DataFrame([{"question": t["question"][:80], "latency_s": t["latency_s"], "cost_usd": t["cost_usd"],
                                   "iterations": t["iterations"]} for t in top]), use_container_width=True)

    with st.expander("Trace explorer"):
        rid = st.selectbox("Trace", [t["request_id"] for t in reversed(traces)],
                           format_func=lambda i: by_id[i]["question"][:80])
        full = store.load_trace(rid)
        st.write(full["answer"])
        st.dataframe(pd.DataFrame([{k: s[k] for k in ("seq", "node", "iteration", "latency_s", "llm_calls",
                                                      "prompt_tokens", "completion_tokens", "cost_usd")}
                                   for s in full["spans"]]), use_container_width=True)


if __name__ == "__main__":
    st.set_page_config(page_title="ATLAS Monitoring", layout="wide")
    render()
