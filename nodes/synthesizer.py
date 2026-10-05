# nodes/synthesizer.py
from openai import OpenAI
from pydantic import BaseModel
from config import OPENAI_API_KEY
from models import model_for

client = OpenAI(api_key=OPENAI_API_KEY)

class SynthesizerOutput(BaseModel):
    answer: str   # full answer with inline citations

SYNTHESIZER_PROMPT = """You are a technical support assistant for Ricoh printers and copiers.

Answer the question using ONLY the provided evidence chunks. For every claim you make,
add an inline citation in this exact format: [Doc Filename | Section | Page X]

Rules:
- Never invent information not in the evidence
- If evidence is partial, say so explicitly
- Use numbered steps for procedural answers
- Be concise and clear"""

def run_synthesizer(state: dict) -> dict:
    chunks_text = "\n\n".join(
        f"[{c['doc']} | {c['section']} | p.{c['page']}]\n{c['text']}"
        for c in state["retrieved_chunks"]
    )
    response = client.beta.chat.completions.parse(
        model=model_for("synthesizer"),
        messages=[
            {"role": "system", "content": SYNTHESIZER_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Question: {state['question']}\n\n"
                    f"Evidence:\n{chunks_text}"
                ),
            },
        ],
        response_format=SynthesizerOutput,
        temperature=0,
    )
    parsed: SynthesizerOutput = response.choices[0].message.parsed
    state["draft_answer"] = parsed.answer
    return state
