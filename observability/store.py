"""SQLite store: traces, spans, user feedback, online eval scores."""
import json
import os
import sqlite3
import threading
from contextlib import contextmanager

DB_PATH = os.getenv("ATLAS_DB_PATH", os.path.join(os.path.dirname(__file__), "atlas.db"))
_lock = threading.Lock()

SCHEMA = """
CREATE TABLE IF NOT EXISTS traces (
    request_id TEXT PRIMARY KEY,
    ts REAL NOT NULL,
    source TEXT NOT NULL,            -- app | eval | ...
    run_id TEXT,                     -- eval run label
    version TEXT,                    -- config/version tag
    question TEXT,
    intent TEXT,
    subquestions TEXT,               -- json
    chunks TEXT,                     -- json: final retrieved chunks (id, doc, section, page, scores, text)
    answer TEXT,
    draft_answer TEXT,
    citations TEXT,                  -- json
    uncertainty_flag INTEGER,
    evidence_sufficient INTEGER,
    confidence_score INTEGER,
    iterations INTEGER,
    abstained INTEGER,
    latency_s REAL,
    prompt_tokens INTEGER,
    completion_tokens INTEGER,
    cost_usd REAL,
    error TEXT
);
CREATE INDEX IF NOT EXISTS idx_traces_ts ON traces(ts);
CREATE TABLE IF NOT EXISTS spans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id TEXT NOT NULL,
    seq INTEGER NOT NULL,
    node TEXT NOT NULL,
    iteration INTEGER,
    latency_s REAL,
    llm_calls INTEGER,
    prompt_tokens INTEGER,
    completion_tokens INTEGER,
    cost_usd REAL,
    output TEXT,                     -- json summary of node output
    error TEXT
);
CREATE INDEX IF NOT EXISTS idx_spans_req ON spans(request_id);
CREATE TABLE IF NOT EXISTS feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id TEXT NOT NULL,
    ts REAL NOT NULL,
    rating INTEGER,                  -- 1 up, -1 down
    wrong_citation INTEGER DEFAULT 0,
    comment TEXT
);
CREATE TABLE IF NOT EXISTS online_evals (
    request_id TEXT PRIMARY KEY,
    ts REAL NOT NULL,
    judge_model TEXT,
    groundedness REAL,
    citation_precision REAL,
    citation_recall REAL,
    citation_validity REAL,
    relevance REAL,
    abstained INTEGER,
    n_claims INTEGER,
    details TEXT
);
"""


@contextmanager
def connect(path: str | None = None):
    conn = sqlite3.connect(path or DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init(path: str | None = None):
    with _lock, connect(path) as c:
        c.executescript(SCHEMA)


def _j(v):
    return json.dumps(v, default=str, ensure_ascii=False)


def save_trace(trace: dict, spans: list[dict], path: str | None = None):
    init(path)
    cols = ["request_id", "ts", "source", "run_id", "version", "question", "intent", "subquestions",
            "chunks", "answer", "draft_answer", "citations", "uncertainty_flag", "evidence_sufficient",
            "confidence_score", "iterations", "abstained", "latency_s", "prompt_tokens",
            "completion_tokens", "cost_usd", "error"]
    row = {k: trace.get(k) for k in cols}
    for k in ("subquestions", "chunks", "citations"):
        row[k] = _j(row[k]) if row[k] is not None else None
    for k in ("uncertainty_flag", "evidence_sufficient", "abstained"):
        row[k] = None if row[k] is None else int(bool(row[k]))
    with _lock, connect(path) as c:
        c.execute(f"INSERT OR REPLACE INTO traces ({','.join(cols)}) VALUES ({','.join('?' * len(cols))})",
                  [row[k] for k in cols])
        c.execute("DELETE FROM spans WHERE request_id=?", (trace["request_id"],))
        for s in spans:
            c.execute(
                "INSERT INTO spans (request_id, seq, node, iteration, latency_s, llm_calls, prompt_tokens,"
                " completion_tokens, cost_usd, output, error) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (trace["request_id"], s["seq"], s["node"], s.get("iteration"), s["latency_s"],
                 s.get("llm_calls", 0), s.get("prompt_tokens", 0), s.get("completion_tokens", 0),
                 s.get("cost_usd", 0.0), _j(s.get("output")), s.get("error")))


def save_feedback(request_id: str, rating: int | None, wrong_citation: bool = False,
                  comment: str = "", ts: float | None = None, path: str | None = None):
    import time
    init(path)
    with _lock, connect(path) as c:
        c.execute("INSERT INTO feedback (request_id, ts, rating, wrong_citation, comment) VALUES (?,?,?,?,?)",
                  (request_id, ts or time.time(), rating, int(wrong_citation), comment))


def save_online_eval(row: dict, path: str | None = None):
    init(path)
    cols = ["request_id", "ts", "judge_model", "groundedness", "citation_precision", "citation_recall",
            "citation_validity", "relevance", "abstained", "n_claims", "details"]
    r = dict(row)
    r["details"] = _j(r.get("details", {}))
    with _lock, connect(path) as c:
        c.execute(f"INSERT OR REPLACE INTO online_evals ({','.join(cols)}) VALUES ({','.join('?' * len(cols))})",
                  [r.get(k) for k in cols])


def query(sql: str, params: tuple = (), path: str | None = None) -> list[dict]:
    init(path)
    with connect(path) as c:
        return [dict(r) for r in c.execute(sql, params).fetchall()]


def load_trace(request_id: str, path: str | None = None) -> dict | None:
    rows = query("SELECT * FROM traces WHERE request_id=?", (request_id,), path)
    if not rows:
        return None
    t = rows[0]
    for k in ("subquestions", "chunks", "citations"):
        t[k] = json.loads(t[k]) if t.get(k) else []
    t["spans"] = query("SELECT * FROM spans WHERE request_id=? ORDER BY seq", (request_id,), path)
    for s in t["spans"]:
        s["output"] = json.loads(s["output"]) if s.get("output") else None
    return t
