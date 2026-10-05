"""Generation-quality metrics: groundedness, citation accuracy, correctness, abstention."""
from pydantic import BaseModel

from evals.judges import format_chunks, judge
from observability.citations import page_matches, parse_citations, parse_marker, resolve_citation


# ── claim-level groundedness + citation accuracy ─────────────────────────────
class ClaimJudgement(BaseModel):
    claim: str
    needs_citation: bool                 # factual statement from the docs (False for "not found" notes etc.)
    citation_markers: list[str]          # verbatim [..|..|..] markers attached to this claim
    supporting_chunk_ids: list[str]      # ids of ALL provided chunks that support it (empty = unsupported)


class ClaimsOutput(BaseModel):
    claims: list[ClaimJudgement]


CLAIMS_SYSTEM = """You audit an answer produced by a RAG system.
1. Split the ANSWER into atomic factual claims (one verifiable fact each). Skip greetings and pure
   meta statements; for statements such as "X was not found in the documentation" set needs_citation=false.
2. For each claim list the citation markers (like [Doc | Section | Page 3]) that COVER it, copied verbatim
   including the square brackets. A marker covers every claim in the sentence it ends; a marker placed at the end
   of a numbered/bulleted list or paragraph covers all claims in that list or paragraph. Claims with no marker
   covering them get an empty list.
3. For each claim, list the ids of every provided CHUNK that directly supports it. A chunk supports a claim
   only if the chunk text states or clearly entails it. If no chunk supports it, return an empty list.
Be strict: do not use outside knowledge."""


def evaluate_claims(answer: str, chunks: list[dict]) -> dict:
    cites = parse_citations(answer)
    if not answer.strip():
        return {"n_claims": 0, "groundedness": None, "claims": [], **_cite_stats([], [], cites, chunks)}
    out = judge(ClaimsOutput, CLAIMS_SYSTEM, f"ANSWER:\n{answer}\n\nCHUNKS:\n{format_chunks(chunks)}")
    return score_claims(out.claims, cites, chunks)


def score_claims(claims: list[ClaimJudgement], cites: list[dict], chunks: list[dict]) -> dict:
    factual = [c for c in claims if c.needs_citation]
    grounded = [c for c in factual if c.supporting_chunk_ids]
    return {
        "n_claims": len(factual),
        "groundedness": (len(grounded) / len(factual)) if factual else None,
        "claims": [c.model_dump() for c in claims],
        **_cite_stats(claims, factual, cites, chunks),
    }


def _cite_stats(claims, factual, cites, chunks) -> dict:
    by_id = {c["id"]: c for c in chunks}
    resolved = [(c, resolve_citation(c, chunks)) for c in cites]
    validity = (sum(r is not None for _, r in resolved) / len(resolved)) if resolved else None

    def marker_to_chunk(marker: str):
        cite = parse_marker(marker)
        return (cite, resolve_citation(cite, chunks)) if cite else (None, None)

    correct = total = 0
    claims_with_correct = 0
    for cl in factual:
        ok_any = False
        for m in cl.citation_markers:
            cite, ch = marker_to_chunk(m)
            if cite is None:
                continue
            total += 1
            if ch is not None and ch["id"] in cl.supporting_chunk_ids and page_matches(cite["page"], ch.get("page")):
                correct += 1
                ok_any = True
        claims_with_correct += ok_any
    supported = [c for c in factual if c.supporting_chunk_ids]
    return {
        "citation_validity": validity,  # citations that point at a really-retrieved chunk (fabrication check)
        "citation_precision": (correct / total) if total else (None if not factual else 0.0),
        "citation_recall": (claims_with_correct / len(supported)) if supported else None,
        "n_citations": len(cites),
    }


# ── correctness vs reference, relevance, abstention ──────────────────────────
class CorrectnessOutput(BaseModel):
    facts_covered: list[bool]            # one per key fact, same order as provided
    contradicts_reference: bool
    correctness: float                   # 0..1, factual agreement with the reference
    relevance: float                     # 0..1, does it address the question asked
    abstains: bool                       # answer says the information is unavailable / insufficient evidence
    reasoning: str


CORRECT_SYSTEM = """You grade a candidate answer against a reference answer.
- facts_covered: for each KEY FACT (in order) true if the candidate states it (paraphrase is fine).
- contradicts_reference: true if the candidate asserts something that conflicts with the reference.
- correctness: 1.0 = fully agrees and complete; 0.5 = partially correct/incomplete; 0.0 = wrong or empty.
  Extra correct detail is not penalised. Citations and formatting are irrelevant here.
- relevance: how directly the candidate addresses the QUESTION (0..1).
- abstains: true if the candidate mainly says the information was not found / evidence is insufficient."""


def evaluate_correctness(question: str, answer: str, reference: str, key_facts: list[str]) -> dict:
    facts = key_facts or []
    user = (f"QUESTION: {question}\n\nREFERENCE ANSWER:\n{reference}\n\nKEY FACTS:\n"
            + ("\n".join(f"{i+1}. {f}" for i, f in enumerate(facts)) or "(none)")
            + f"\n\nCANDIDATE ANSWER:\n{answer}")
    o = judge(CorrectnessOutput, CORRECT_SYSTEM, user)
    cov = o.facts_covered[:len(facts)]
    fact_cov = (sum(cov) / len(facts)) if facts else None
    corr = 0.0 if o.contradicts_reference and o.correctness > 0.5 else o.correctness
    return {"correctness": corr, "fact_coverage": fact_cov, "relevance": o.relevance,
            "abstains": o.abstains, "contradicts": o.contradicts_reference, "reasoning": o.reasoning}


def abstention_score(expected_answerable: bool, abstained: bool) -> dict:
    """Abstention correctness: unanswerable -> must abstain; answerable -> must not."""
    return {"abstention_correct": float(abstained != expected_answerable),
            "false_abstain": float(abstained and expected_answerable),
            "hallucinated_answer": float((not abstained) and (not expected_answerable))}
