# nodes/analyzer.py
import re
from openai import OpenAI
from pydantic import BaseModel
from config import OPENAI_API_KEY
from models import model_for

client = OpenAI(api_key=OPENAI_API_KEY)

class AnalyzerOutput(BaseModel):
    confidence_score: int    # 0-10
    sufficient: bool
    subject_matches: bool    # evidence is about the same product/component/scope the question asks about
    answer_quote: str        # verbatim sentence from the evidence that answers the question ("" if none)
    missing: str
    reasoning: str

ANALYZER_PROMPT = """You are an evidence quality checker for a technical support agent.

Score the evidence from 0-10 using these anchors:
- 10: Evidence completely answers the question with no gaps
- 7:  Evidence covers the main answer but misses minor details
- 5:  Evidence is relevant but only partially answers the question
- 3:  Evidence is loosely related but does not answer the question
- 0:  Evidence is completely irrelevant or missing

Be strict about SCOPE. Evidence on a related topic is NOT evidence for the question: if the question asks about X
(e.g. a third-party operating system, pricing, licensing, hardware sizing) and the evidence only covers a different
thing that merely shares words with X (e.g. the product's own tuning settings), score it 3 or lower.

Fill the extra fields honestly:
- subject_matches: true only if the evidence is about exactly what the question asks about.
- answer_quote: copy ONE sentence verbatim from the evidence that directly answers the question. If no sentence
  does, return an empty string. Never paraphrase or invent a quote.

Set sufficient = true if confidence_score >= 7, otherwise false.
If not sufficient, describe exactly what is missing."""

def _tokens(s: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", (s or "").lower())


def quote_supported(quote: str, chunks: list[dict], min_overlap: float = 0.9) -> bool:
    """True if (almost) all words of the quote occur in one retrieved chunk, i.e. the quote is not invented."""
    q = _tokens(quote)
    if len(q) < 3:
        return False
    for c in chunks:
        words = set(_tokens(c.get("text", "")))
        if sum(w in words for w in q) / len(q) >= min_overlap:
            return True
    return False


def decide_sufficient(parsed, chunks: list[dict]) -> bool:
    """Sufficiency is decided here, not by the model's own flag: it must be confident, on-subject, and
    able to point at a real sentence in the evidence that answers the question."""
    return (bool(chunks) and parsed.confidence_score >= 7 and parsed.subject_matches
            and quote_supported(parsed.answer_quote, chunks))


def run_analyzer(state: dict) -> dict:
    chunks_text = "\n\n".join(
        f"[{c['doc']} | {c['section']} | p.{c['page']}]\n{c['text']}"
        for c in state["retrieved_chunks"]
    )
    response = client.beta.chat.completions.parse(
        model=model_for("analyzer"),
        messages=[
            {"role": "system", "content": ANALYZER_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Question: {state['question']}\n"
                    f"Intent: {state['intent']}\n\n"
                    f"Evidence:\n{chunks_text}"
                ),
            },
        ],
        response_format=AnalyzerOutput,
        temperature=0,
    )
    parsed: AnalyzerOutput = response.choices[0].message.parsed
    state["confidence_score"]    = parsed.confidence_score
    state["evidence_sufficient"] = decide_sufficient(parsed, state["retrieved_chunks"])
    state["subject_matches"]     = parsed.subject_matches
    state["missing_info"]        = parsed.missing or (
        "" if state["evidence_sufficient"] else "The evidence does not directly answer the question.")
    return state
