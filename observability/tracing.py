"""Tracer: records one trace per question and one span per agent-node execution.

Every trace lands in SQLite (always) and is additionally exported to Langfuse
when LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY are set (optional).
"""
import os
import subprocess
import time
import uuid

from observability import store, usage
from observability.citations import is_abstention, parse_citations, resolve_citation
from observability.logging import get_logger, request_id_var

log = get_logger("atlas.trace")
_VERSION = None


def get_version() -> str:
    global _VERSION
    if _VERSION is None:
        _VERSION = os.getenv("ATLAS_VERSION") or ""
        if not _VERSION:
            try:
                _VERSION = subprocess.check_output(
                    ["git", "rev-parse", "--short", "HEAD"], stderr=subprocess.DEVNULL,
                    cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))).decode().strip()
            except Exception:
                _VERSION = "unknown"
    return _VERSION


def _chunk_view(c: dict, with_text=True) -> dict:
    d = {k: c.get(k) for k in ("id", "doc", "section", "page", "breadcrumb", "doc_type", "score", "rerank_score")}
    if with_text:
        d["text"] = c.get("text", "")
    return d


def summarize_node(node: str, state: dict) -> dict:
    if node == "planner":
        return {"intent": state.get("intent"), "subquestions": state.get("subquestions")}
    if node == "retriever":
        return {"chunk_ids": [c["id"] for c in state.get("retrieved_chunks", [])],
                "scores": [c.get("rerank_score") for c in state.get("retrieved_chunks", [])],
                "subquestions": state.get("subquestions")}
    if node == "analyzer":
        return {"confidence_score": state.get("confidence_score"),
                "sufficient": state.get("evidence_sufficient"), "subject_matches": state.get("subject_matches"),
                "missing": state.get("missing_info")}
    if node == "refiner":
        return {"subquestions": state.get("subquestions")}
    if node == "synthesizer":
        return {"draft_chars": len(state.get("draft_answer", ""))}
    if node == "verifier":
        return {"uncertainty_flag": state.get("uncertainty_flag"),
                "answer_chars": len(state.get("final_answer", ""))}
    return {}


class Tracer:
    def __init__(self, question: str, source: str = "app", run_id: str | None = None,
                 version: str | None = None):
        usage.install()
        self.request_id = uuid.uuid4().hex
        self.question, self.source, self.run_id = question, source, run_id
        self.version = version or get_version()
        self.spans: list[dict] = []
        self.total = usage.Usage()
        self.t0 = time.time()
        self._rid_token = request_id_var.set(self.request_id)
        self._iteration = 0
        log.info("trace_start", extra={"fields": {"question": question, "source": source}})

    def run(self, node: str, fn, state: dict, *args):
        """Execute fn(state, *args) as a traced span and return its result."""
        u, token = usage.start_collecting()
        t = time.time()
        err = None
        try:
            return fn(state, *args)
        except Exception as e:  # recorded, then re-raised
            err = f"{type(e).__name__}: {e}"
            raise
        finally:
            usage.stop_collecting(token)
            latency = time.time() - t
            if node == "refiner":
                self._iteration += 1
            out = {}
            if err is None:
                try:
                    out = summarize_node(node, state)
                except Exception:
                    pass
            span = {"seq": len(self.spans), "node": node, "iteration": self._iteration,
                    "latency_s": round(latency, 4), "output": out, "error": err, **u.as_dict()}
            self.spans.append(span)
            self.total.calls += u.calls
            self.total.prompt_tokens += u.prompt_tokens
            self.total.completion_tokens += u.completion_tokens
            self.total.cost_usd += u.cost_usd
            log.info("span", extra={"fields": {"node": node, "latency_s": span["latency_s"],
                                                "cost_usd": span["cost_usd"], "error": err}})

    def finish(self, state: dict, error: str | None = None) -> dict:
        chunks = state.get("retrieved_chunks", [])
        answer = state.get("final_answer", "")
        cites = []
        for c in parse_citations(answer):
            hit = resolve_citation(c, chunks)
            cites.append({"doc": c["doc"], "section": c["section"], "page": c["page"],
                          "resolved_chunk_id": hit["id"] if hit else None})
        trace = {
            "request_id": self.request_id, "ts": self.t0, "source": self.source, "run_id": self.run_id,
            "version": self.version, "question": self.question, "intent": state.get("intent"),
            "subquestions": state.get("subquestions"), "chunks": [_chunk_view(c) for c in chunks],
            "answer": answer, "draft_answer": state.get("draft_answer"), "citations": cites,
            "uncertainty_flag": state.get("uncertainty_flag"),
            "evidence_sufficient": state.get("evidence_sufficient"),
            "confidence_score": state.get("confidence_score"),
            "iterations": state.get("iteration_count"),
            "abstained": is_abstention(answer, chunks) if not error else None,
            "latency_s": round(time.time() - self.t0, 4),
            "prompt_tokens": self.total.prompt_tokens, "completion_tokens": self.total.completion_tokens,
            "cost_usd": round(self.total.cost_usd, 6), "error": error,
        }
        try:
            store.save_trace(trace, self.spans)
        except Exception as e:  # observability must never take the app down
            log.error("trace_save_failed", extra={"fields": {"err": str(e)}})
        try:
            from observability.langfuse_export import export_trace
            export_trace(trace, self.spans)
        except Exception as e:
            log.warning("langfuse_export_failed", extra={"fields": {"err": str(e)}})
        log.info("trace_end", extra={"fields": {"latency_s": trace["latency_s"],
                                                 "cost_usd": trace["cost_usd"], "error": error}})
        request_id_var.reset(self._rid_token)
        return trace
