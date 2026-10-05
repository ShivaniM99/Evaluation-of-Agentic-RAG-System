# pipeline.py
from index_loader import load_index
from nodes.planner import run_planner
from nodes.retriever import run_retriever
from nodes.analyzer import run_analyzer
from nodes.query_refiner import run_query_refiner
from nodes.synthesizer import run_synthesizer
from verifier import run_verifier
from config import MAX_ITERATIONS
from answers import NO_EVIDENCE_ANSWER
from observability.tracing import Tracer


def run_pipeline_streaming(question: str, index, source: str = "app", run_id: str | None = None):
    """
    Runs each agent node manually and yields state after each one
    so the UI can show live progress.

    Every run is traced (per-node latency / tokens / cost) into the SQLite store;
    each yielded update carries the `request_id` of its trace.
    """
    tracer = Tracer(question, source=source, run_id=run_id)

    # --- Initial State ---
    state = {
        "question":            question,
        "intent":              "",
        "subquestions":        [],
        "retrieved_chunks":    [],
        "evidence_sufficient": False,
        "confidence_score":    0,
        "missing_info":        "",
        "iteration_count":     0,
        "draft_answer":        "",
        "final_answer":        "",
        "uncertainty_flag":    False,
        "subject_matches":     True,
    }
    rid = tracer.request_id

    try:
        # ── NODE 1: PLANNER ──────────────────────────────────────────
        state = tracer.run("planner", run_planner, state)
        yield {**state, "stage": "planner", "request_id": rid}

        # ── NODE 2 + 3 + 4 LOOP: RETRIEVER → ANALYZER → REFINER ─────
        while True:

            # Node 2 — Retriever
            state = tracer.run("retriever", run_retriever, state, index)
            yield {
                **state,
                "stage":       "retriever",
                "chunk_count": len(state["retrieved_chunks"]),
                "request_id":  rid,
            }

            # Node 3 — Analyzer
            state = tracer.run("analyzer", run_analyzer, state)
            yield {
                **state,
                "stage":      "analyzer",
                "sufficient": state["evidence_sufficient"],
                "request_id": rid,
            }

            # Exit loop if evidence is good enough or max iterations hit
            if state["evidence_sufficient"] or state["iteration_count"] >= MAX_ITERATIONS:
                break

            # Node 4 — Query Refiner (only runs if evidence insufficient)
            state = tracer.run("refiner", run_query_refiner, state)
            yield {**state, "stage": "refiner", "request_id": rid}

        # Abstain when there is nothing to answer from, or when refinement ran out and the evidence is still about
        # something other than what was asked (related-sounding but off-subject text invites a confident hallucination).
        # Thin-but-on-subject evidence still gets a partial answer from the synthesizer.
        off_subject = not state["evidence_sufficient"] and not state["subject_matches"]
        if state["retrieved_chunks"] and not off_subject:
            # ── NODE 5: SYNTHESIZER ──────────────────────────────────
            state = tracer.run("synthesizer", run_synthesizer, state)
            yield {**state, "stage": "synthesizer", "request_id": rid}

            # ── POST-LOOP: VERIFIER ──────────────────────────────────
            state = tracer.run("verifier", run_verifier, state)
        else:
            # Abstain without calling the LLM.
            state["draft_answer"] = state["final_answer"] = NO_EVIDENCE_ANSWER
            state["uncertainty_flag"] = True
    except Exception as e:
        tracer.finish(state, error=f"{type(e).__name__}: {e}")
        raise

    trace = tracer.finish(state)  # persisted before the last update is yielded
    yield {**state, "stage": "verifier", "request_id": rid, "abstained": state["final_answer"] == NO_EVIDENCE_ANSWER,
           "trace": {k: trace[k] for k in ("latency_s", "cost_usd", "prompt_tokens", "completion_tokens")}}
