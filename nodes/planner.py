# nodes/planner.py
from openai import OpenAI
from pydantic import BaseModel
from config import OPENAI_API_KEY
from models import model_for

client = OpenAI(api_key=OPENAI_API_KEY)

class PlannerOutput(BaseModel):
    intent: str          # "lookup" | "procedural" | "compatibility"
    subquestions: list[str]

PLANNER_PROMPT = """You are a technical query planner for a Ricoh printer support system.

Given a user question, decompose it and classify intent.
- "lookup"        = asking for a specific value, code, or setting
- "procedural"    = asking how to do something step-by-step
- "compatibility" = asking if X works with Y

Generate 1-3 focused sub-questions to fully answer the main query."""

def run_planner(state: dict) -> dict:
    response = client.beta.chat.completions.parse(
        model=model_for("planner"),
        messages=[
            {"role": "system", "content": PLANNER_PROMPT},
            {"role": "user",   "content": state["question"]},
        ],
        response_format=PlannerOutput,
        temperature=0,
    )
    parsed: PlannerOutput = response.choices[0].message.parsed
    state["intent"]          = parsed.intent
    state["subquestions"]    = parsed.subquestions
    state["iteration_count"] = 0
    return state
