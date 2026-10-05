"""Optional Langfuse export through its public ingestion REST API (no SDK dependency).

Enabled only when LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY are set.
LANGFUSE_HOST defaults to https://cloud.langfuse.com (point it at a self-hosted instance if you prefer).
"""
import os
import uuid
from datetime import datetime, timezone


def enabled() -> bool:
    return bool(os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY"))


def _iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()


def build_batch(trace: dict, spans: list[dict]) -> list[dict]:
    tid = trace["request_id"]
    t0 = trace["ts"]
    events = [{
        "id": uuid.uuid4().hex, "type": "trace-create", "timestamp": _iso(t0),
        "body": {"id": tid, "name": "atlas-query", "timestamp": _iso(t0), "input": trace["question"],
                 "output": trace["answer"], "version": trace.get("version"),
                 "tags": [trace["source"]] + ([trace["run_id"]] if trace.get("run_id") else []),
                 "metadata": {"iterations": trace.get("iterations"), "abstained": trace.get("abstained"),
                              "uncertainty_flag": trace.get("uncertainty_flag"),
                              "cost_usd": trace.get("cost_usd")}},
    }]
    cursor = t0
    for s in spans:
        start, end = cursor, cursor + s["latency_s"]
        cursor = end
        events.append({
            "id": uuid.uuid4().hex, "type": "span-create", "timestamp": _iso(start),
            "body": {"id": uuid.uuid4().hex, "traceId": tid, "name": s["node"],
                     "startTime": _iso(start), "endTime": _iso(end), "output": s.get("output"),
                     "level": "ERROR" if s.get("error") else "DEFAULT", "statusMessage": s.get("error"),
                     "metadata": {k: s.get(k) for k in ("iteration", "llm_calls", "prompt_tokens",
                                                         "completion_tokens", "cost_usd")}},
        })
    return events


def export_trace(trace: dict, spans: list[dict]):
    if not enabled():
        return
    import requests
    host = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com").rstrip("/")
    r = requests.post(f"{host}/api/public/ingestion", json={"batch": build_batch(trace, spans)},
                      auth=(os.environ["LANGFUSE_PUBLIC_KEY"], os.environ["LANGFUSE_SECRET_KEY"]), timeout=10)
    r.raise_for_status()
