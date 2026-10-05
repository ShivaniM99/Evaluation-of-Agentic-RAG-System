"""Threshold alerts over window KPIs. Override any threshold with env ATLAS_ALERT_<NAME>."""
import os

DEFAULTS = {  # name: (comparator, threshold, severity, human message)
    "groundedness":       ("min", 0.85, "critical", "Groundedness below target"),
    "citation_precision": ("min", 0.80, "critical", "Citation precision below target"),
    "citation_validity":  ("min", 0.95, "critical", "Fabricated citations detected"),
    "error_rate":         ("max", 0.05, "critical", "Pipeline error rate high"),
    "abstention_rate":    ("max", 0.40, "warning",  "Abstention rate high (retrieval/coverage issue?)"),
    "hit_max_iter_rate":  ("max", 0.35, "warning",  "Many queries exhaust refiner iterations"),
    "latency_p95":        ("max", 45.0, "warning",  "p95 latency high (seconds)"),
    "avg_cost_usd":       ("max", 0.05, "warning",  "Average cost per query high"),
    "thumbs_up_rate":     ("min", 0.70, "warning",  "User satisfaction low"),
}


def thresholds() -> dict:
    out = {}
    for k, (cmp_, thr, sev, msg) in DEFAULTS.items():
        env = os.getenv(f"ATLAS_ALERT_{k.upper()}")
        out[k] = (cmp_, float(env) if env else thr, sev, msg)
    return out


def compute_alerts(k: dict, min_queries: int = 5) -> list[dict]:
    if k.get("n_queries", 0) < min_queries:
        return []
    alerts = []
    for name, (cmp_, thr, sev, msg) in thresholds().items():
        v = k.get(name)
        if v is None:
            continue
        if (cmp_ == "min" and v < thr) or (cmp_ == "max" and v > thr):
            alerts.append({"metric": name, "value": v, "threshold": thr, "severity": sev, "message": msg})
    if k.get("wrong_citation_reports", 0) >= 3:
        alerts.append({"metric": "wrong_citation_reports", "value": k["wrong_citation_reports"], "threshold": 3,
                       "severity": "warning", "message": "Users are reporting wrong citations"})
    return sorted(alerts, key=lambda a: a["severity"] != "critical")
