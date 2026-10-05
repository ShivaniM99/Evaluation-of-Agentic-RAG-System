import math

from evals import stats
from evals.metrics import generation as gen
from evals.metrics.retrieval import mrr, ndcg_at_k, precision_at_k, recall_at_k, retrieval_metrics
from evals.metrics.trajectory import trajectory_metrics
from observability.citations import is_abstention, parse_citations, resolve_citation

CH = [
    {"id": "a_chunk_0", "doc": "a.pdf", "section": "Enabling objects", "page": "1-1", "text": "x"},
    {"id": "b_chunk_0", "doc": "b.pdf", "section": "Version 3.12.2", "page": "1-4", "text": "y"},
]


def test_retrieval_basic():
    ranked, gold = ["x", "a", "b"], {"a", "b"}
    assert recall_at_k(ranked, gold, 1) == 0
    assert recall_at_k(ranked, gold, 3) == 1
    assert math.isclose(precision_at_k(ranked, gold, 3), 2 / 3)
    assert mrr(ranked, gold) == 0.5
    assert 0 < ndcg_at_k(ranked, gold, 3) < 1
    assert ndcg_at_k(["a", "b"], gold, 2) == 1
    assert mrr(ranked, set()) is None


def test_retrieval_metrics_doc_level():
    m = retrieval_metrics(["a_chunk_1", "z_chunk_0"], {"a_chunk_0"})
    assert m["recall@5"] == 0 and m["doc_hit@5"] == 1.0 and m["context_precision"] == 0.5


def test_citation_parse_and_resolve():
    ans = "Set it to Yes [a.pdf | Enabling objects | Page 1]. FusionPro exists [b | Version 3.12.2 | p.1-4]. Bogus [zzz.pdf | Nope | Page 9]."
    cites = parse_citations(ans)
    assert [c["doc"] for c in cites] == ["a.pdf", "b", "zzz.pdf"]
    assert resolve_citation(cites[0], CH)["id"] == "a_chunk_0"
    assert resolve_citation(cites[1], CH)["id"] == "b_chunk_0"  # tolerates missing .pdf
    assert resolve_citation(cites[2], CH) is None


def test_abstention_detection():
    assert is_abstention("", [])
    assert is_abstention("There is insufficient evidence in the docs.", CH)
    # partial answer with a "not found" note but real citations is NOT an abstention
    assert not is_abstention("Do X [a.pdf | Enabling objects | Page 1]. Note: Y was not found in the available documentation.", CH)


def _cj(claim, markers, support, needs=True):
    return gen.ClaimJudgement(claim=claim, needs_citation=needs, citation_markers=markers, supporting_chunk_ids=support)


def test_score_claims_groundedness_and_citations():
    m_ok = "[a.pdf | Enabling objects | Page 1]"
    m_wrong = "[b.pdf | Version 3.12.2 | Page 1-4]"
    ans = f"c1 {m_ok} c2 {m_wrong} c3 and a fake [q.pdf | S | Page 1]"
    claims = [
        _cj("c1", [m_ok], ["a_chunk_0"]),                        # supported + correct citation
        _cj("c2", [m_wrong], ["a_chunk_0"]),                     # supported, but cited the wrong chunk
        _cj("c3", [], []),                                       # unsupported, uncited
        _cj("note", [], [], needs=False),                        # ignored
    ]
    r = gen.score_claims(claims, parse_citations(ans), CH)
    assert r["n_claims"] == 3
    assert math.isclose(r["groundedness"], 2 / 3)
    assert math.isclose(r["citation_precision"], 0.5)   # 1 of 2 claim-citations right
    assert math.isclose(r["citation_recall"], 0.5)      # 1 of 2 supported claims has a correct citation
    assert math.isclose(r["citation_validity"], 2 / 3)  # fake citation does not resolve


def test_abstention_score():
    assert gen.abstention_score(False, True)["abstention_correct"] == 1
    assert gen.abstention_score(False, False)["hallucinated_answer"] == 1
    assert gen.abstention_score(True, True)["false_abstain"] == 1


def test_kappa_and_stats():
    assert stats.cohens_kappa([1, 1, 0, 0], [1, 1, 0, 0]) == 1.0
    assert abs(stats.cohens_kappa([1, 0, 1, 0], [0, 1, 0, 1]) + 1) < 1e-9
    assert stats.cohens_kappa([1, 1, 1, 0], [1, 1, 0, 0]) == 0.5
    assert stats.percentile([1, 2, 3, 4], .5) == 2.5
    assert stats.mean([None, 2, 4]) == 3


def test_trajectory_metrics():
    spans = [
        {"node": "retriever", "latency_s": 1, "output": {"chunk_ids": ["x"]}, "llm_calls": 2},
        {"node": "analyzer", "latency_s": 1, "output": {"sufficient": False}, "llm_calls": 1},
        {"node": "refiner", "latency_s": 1, "output": {}, "llm_calls": 1},
        {"node": "retriever", "latency_s": 1, "output": {"chunk_ids": ["x", "gold"]}, "llm_calls": 2},
        {"node": "analyzer", "latency_s": 1, "output": {"sufficient": True}, "llm_calls": 1},
    ]
    t = trajectory_metrics({"spans": spans, "cost_usd": 0.01, "latency_s": 5}, {"gold"}, True, 3)
    assert t["iterations"] == 1 and t["refiner_helped"] == 1.0 and t["terminated_sufficient"] == 1.0
    assert t["analyzer_decision_correct"] == 1.0 and t["llm_calls"] == 7
    # unanswerable but analyzer said sufficient -> wrong decision
    t2 = trajectory_metrics({"spans": spans, "cost_usd": 0, "latency_s": 1}, set(), False, 3)
    assert t2["analyzer_decision_correct"] == 0.0


def test_marker_parsing_accepts_bracketless_judge_output():
    from observability.citations import parse_marker
    a = parse_marker("a.pdf | Enabling objects | p.1-1")
    b = parse_marker("[a.pdf | Enabling objects | p.1-1]")
    assert a and b and a["doc"] == b["doc"] == "a.pdf" and a["page"] == "1-1"
    assert resolve_citation(a, CH)["id"] == "a_chunk_0"
    assert parse_marker("garbage") is None


def test_bracketless_markers_are_scored():
    marker = "a.pdf | Enabling objects | p.1-1"            # what the judge actually returns
    claims = [_cj("c1", [marker], ["a_chunk_0"])]
    r = gen.score_claims(claims, parse_citations(f"c1 [{marker}]"), CH)
    assert r["citation_precision"] == 1.0 and r["citation_recall"] == 1.0


def test_abstention_requires_the_answer_to_say_so():
    from answers import NO_EVIDENCE_ANSWER
    assert is_abstention(NO_EVIDENCE_ANSWER, [])
    # an answer asserted from empty retrieval is a hallucination, not an abstention
    assert not is_abstention("The licensing model is subscription based with volume discounts.", [])


def test_analyzer_sufficiency_needs_real_quote_and_matching_subject():
    from types import SimpleNamespace as NS
    from nodes.analyzer import decide_sufficient, quote_supported
    chunks = [{"text": "To enable printers after a restart, set Remember enabled status of printers to Yes."}]
    good = NS(confidence_score=9, subject_matches=True, answer_quote="set Remember enabled status of printers to Yes")
    assert decide_sufficient(good, chunks)
    assert not decide_sufficient(NS(confidence_score=9, subject_matches=False, answer_quote=good.answer_quote), chunks)
    assert not decide_sufficient(NS(confidence_score=9, subject_matches=True, answer_quote=""), chunks)
    assert not decide_sufficient(NS(confidence_score=9, subject_matches=True,
                                    answer_quote="volume discounts are available for licences"), chunks)   # invented quote
    assert not decide_sufficient(NS(confidence_score=6, subject_matches=True, answer_quote=good.answer_quote), chunks)
    assert not decide_sufficient(good, [])
    assert not quote_supported("ok", chunks)
