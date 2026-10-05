import httpx
import pytest
from openai import OpenAI

import pipeline
from observability import langfuse_export, store, usage
from observability.tracing import Tracer


def test_cost_math():
    assert usage.cost_usd("gpt-4o-mini", 1_000_000, 1_000_000) == pytest.approx(0.75)
    assert usage.cost_usd("gpt-4o-2024-08-06", 1_000_000, 0) == pytest.approx(2.5)  # prefix match
    assert usage.cost_usd("unknown", 10, 10) == 0


def _mock_client():
    def handler(req: httpx.Request):
        if req.url.path.endswith("/embeddings"):
            return httpx.Response(200, json={"object": "list", "model": "text-embedding-3-small", "data": [
                {"object": "embedding", "index": 0, "embedding": [0.1, 0.2]}], "usage": {"prompt_tokens": 7, "total_tokens": 7}})
        return httpx.Response(200, json={
            "id": "x", "object": "chat.completion", "created": 0, "model": "gpt-4o-mini",
            "choices": [{"index": 0, "finish_reason": "stop", "message": {"role": "assistant", "content": "{\"v\": 1}"}}],
            "usage": {"prompt_tokens": 100, "completion_tokens": 20, "total_tokens": 120}})
    return OpenAI(api_key="sk-test", http_client=httpx.Client(transport=httpx.MockTransport(handler)))


def test_usage_wrapper_counts_chat_parse_and_embeddings_once():
    from pydantic import BaseModel

    class V(BaseModel):
        v: int

    usage.install()
    usage.install()  # idempotent
    c = _mock_client()
    u, tok = usage.start_collecting()
    try:
        c.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "user", "content": "hi"}])
        c.beta.chat.completions.parse(model="gpt-4o-mini", messages=[{"role": "user", "content": "hi"}], response_format=V)
        c.embeddings.create(model="text-embedding-3-small", input=["a"])
    finally:
        usage.stop_collecting(tok)
    assert u.calls == 3
    assert u.prompt_tokens == 100 + 100 + 7 and u.completion_tokens == 40
    assert u.cost_usd == pytest.approx(2 * (100 * 0.15 + 20 * 0.6) / 1e6 + 7 * 0.02 / 1e6)


def test_calls_outside_a_collector_are_untouched():
    usage.install()
    r = _mock_client().chat.completions.create(model="gpt-4o-mini", messages=[{"role": "user", "content": "hi"}])
    assert r.usage.prompt_tokens == 100


def _fake_nodes(monkeypatch, sufficient_after=1, fail_at=None, subject_matches=True):
    chunk = {"id": "a_chunk_0", "doc": "a.pdf", "section": "Sec", "page": "1-1", "text": "t", "rerank_score": 0.9}

    def planner(s):
        s.update(intent="lookup", subquestions=["q1"], iteration_count=0)
        return s

    def retriever(s, idx):
        s["retrieved_chunks"] = [chunk]
        return s

    def analyzer(s):
        s.update(confidence_score=8, evidence_sufficient=s["iteration_count"] >= sufficient_after, missing_info="m",
                 subject_matches=subject_matches)
        return s

    def refiner(s):
        s["iteration_count"] += 1
        return s

    def synth(s):
        s["draft_answer"] = "Do it [a.pdf | Sec | Page 1]."
        return s

    def verifier(s):
        if fail_at == "verifier":
            raise RuntimeError("boom")
        s.update(final_answer=s["draft_answer"], uncertainty_flag=False)
        return s

    for n, f in dict(run_planner=planner, run_retriever=retriever, run_analyzer=analyzer, run_query_refiner=refiner,
                     run_synthesizer=synth, run_verifier=verifier).items():
        monkeypatch.setattr(pipeline, n, f)


def test_pipeline_trace_persisted(monkeypatch):
    _fake_nodes(monkeypatch, sufficient_after=1)
    updates = list(pipeline.run_pipeline_streaming("How?", index=None, source="app"))
    rid = updates[-1]["request_id"]
    assert {u["request_id"] for u in updates} == {rid}
    assert updates[-1]["stage"] == "verifier" and "latency_s" in updates[-1]["trace"]
    t = store.load_trace(rid)
    assert [s["node"] for s in t["spans"]] == ["planner", "retriever", "analyzer", "refiner", "retriever", "analyzer",
                                               "synthesizer", "verifier"]
    assert t["iterations"] == 1 and t["abstained"] == 0 and t["error"] is None
    assert t["citations"][0]["resolved_chunk_id"] == "a_chunk_0"
    assert t["spans"][4]["iteration"] == 1
    assert t["version"]


def test_pipeline_error_is_traced_and_reraised(monkeypatch):
    _fake_nodes(monkeypatch, fail_at="verifier")
    with pytest.raises(RuntimeError):
        list(pipeline.run_pipeline_streaming("How?", index=None))
    row = store.query("SELECT * FROM traces")[0]
    assert "boom" in row["error"]
    assert any(s["error"] for s in store.query("SELECT * FROM spans"))


def test_feedback_and_candidates(monkeypatch):
    _fake_nodes(monkeypatch)
    rid = list(pipeline.run_pipeline_streaming("Q?", None))[-1]["request_id"]
    store.save_feedback(rid, -1, comment="bad")
    store.save_feedback(rid, None, wrong_citation=True)
    from monitoring.feedback import failure_candidates
    c = failure_candidates()
    assert len(c) == 1 and c[0]["failing_trace"] == rid and c[0]["source"] == "user-feedback"


def test_langfuse_batch_shape():
    tr = {"request_id": "r1", "ts": 1.0, "question": "q", "answer": "a", "source": "app", "run_id": None,
          "version": "v", "iterations": 0, "abstained": 0, "uncertainty_flag": 0, "cost_usd": 0.1}
    spans = [{"node": "planner", "latency_s": 1.0, "output": {}, "error": None, "iteration": 0, "llm_calls": 1,
              "prompt_tokens": 1, "completion_tokens": 1, "cost_usd": 0.0}]
    b = langfuse_export.build_batch(tr, spans)
    assert b[0]["type"] == "trace-create" and b[1]["type"] == "span-create" and b[1]["body"]["traceId"] == "r1"
    assert not langfuse_export.enabled()


def test_model_for_overrides(monkeypatch):
    import models
    monkeypatch.setattr(models, "OPENAI_CHAT_MODEL", "base-model")
    monkeypatch.setenv("ATLAS_MODEL_SYNTHESIZER", "strong-model")
    assert models.model_for("planner") == "base-model"
    assert models.model_for("synthesizer") == "strong-model"
    assert set(models.all_models()) == set(models.NODES)


def test_judge_routes_anthropic_prefix(monkeypatch, tmp_path):
    from pydantic import BaseModel
    from evals import judges

    class S(BaseModel):
        x: int

    monkeypatch.setattr(judges, "CACHE_PATH", str(tmp_path / "c.jsonl"))
    monkeypatch.setattr(judges, "_cache", {})
    seen = {}

    def fake(model, schema, system, user):
        seen["model"] = model
        return schema(x=3)

    monkeypatch.setattr(judges, "_anthropic_parse", fake)
    out = judges.judge(S, "s", "u", model="anthropic:claude-test")
    assert out.x == 3 and seen["model"] == "claude-test"
    assert judges.judge(S, "s", "u", model="anthropic:claude-test").x == 3  # served from cache


def test_verifier_prompt_requires_preserving_citations():
    import verifier
    p = verifier.VERIFIER_PROMPT
    assert "PRESERVE every inline citation" in p and "[Doc Filename | Section | Page X]" in p


def test_claude_prices_and_judge_billing(monkeypatch, tmp_path):
    assert usage.cost_usd("claude-sonnet-5-5", 1_000_000, 1_000_000) == pytest.approx(12.0)
    assert usage.cost_usd("claude-haiku-4-5-20251001", 1_000_000, 0) == pytest.approx(1.0)  # prefix match
    from pydantic import BaseModel
    from evals import judges

    class S(BaseModel):
        x: int

    monkeypatch.setattr(judges, "CACHE_PATH", str(tmp_path / "c.jsonl"))
    monkeypatch.setattr(judges, "_cache", {})
    base = dict(judges.JUDGE_COST)

    def fake(model, schema, system, user):
        judges._bill("anthropic:" + model, 1000, 100)
        return schema(x=1)

    monkeypatch.setattr(judges, "_anthropic_parse", fake)
    judges.judge(S, "s", "u", model="anthropic:claude-sonnet-5-5")
    judges.judge(S, "s", "u", model="anthropic:claude-sonnet-5-5")        # cache hit: free
    assert judges.JUDGE_COST["calls"] - base["calls"] == 1 and judges.JUDGE_COST["cached"] - base["cached"] == 1
    assert judges.JUDGE_COST["usd"] - base["usd"] == pytest.approx(1000 * 2e-6 + 100 * 10e-6)


def test_pipeline_abstains_without_calling_llm_when_nothing_retrieved(monkeypatch):
    _fake_nodes(monkeypatch)
    monkeypatch.setattr(pipeline, "run_retriever", lambda s, idx: {**s, "retrieved_chunks": []})
    monkeypatch.setattr(pipeline, "run_synthesizer", lambda s: (_ for _ in ()).throw(AssertionError("synth called")))
    monkeypatch.setattr(pipeline, "run_verifier", lambda s: (_ for _ in ()).throw(AssertionError("verifier called")))
    last = list(pipeline.run_pipeline_streaming("licensing?", None))[-1]
    from answers import NO_EVIDENCE_ANSWER
    assert last["final_answer"] == NO_EVIDENCE_ANSWER and last["abstained"] is True
    t = store.load_trace(last["request_id"])
    assert t["abstained"] == 1 and not any(s["node"] in ("synthesizer", "verifier") for s in t["spans"])


def test_pipeline_abstains_when_refinement_ends_off_subject_but_answers_partial_evidence(monkeypatch):
    from answers import NO_EVIDENCE_ANSWER
    # evidence never sufficient AND about the wrong subject -> abstain, no synth call
    _fake_nodes(monkeypatch, sufficient_after=99, subject_matches=False)
    monkeypatch.setattr(pipeline, "run_synthesizer", lambda s: (_ for _ in ()).throw(AssertionError("synth called")))
    last = list(pipeline.run_pipeline_streaming("OS tuning?", None))[-1]
    assert last["final_answer"] == NO_EVIDENCE_ANSWER and last["abstained"] is True
    # evidence never sufficient but ON subject (partial) -> still answers
    _fake_nodes(monkeypatch, sufficient_after=99, subject_matches=True)
    last = list(pipeline.run_pipeline_streaming("partial?", None))[-1]
    assert last["final_answer"].startswith("Do it") and last["abstained"] is False
