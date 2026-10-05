# nodes/query_refiner.py
from openai import OpenAI
from pydantic import BaseModel
from config import OPENAI_API_KEY
from models import model_for

client = OpenAI(api_key=OPENAI_API_KEY)

class RefinerOutput(BaseModel):
    refined_subquestions: list[str]

REFINER_PROMPT = """You are a search query optimizer for a technical document retrieval system.

Given the original question and a description of missing information, generate 1-2 new,
targeted sub-questions to fill the gap.

Do NOT repeat or rephrase already searched queries — explore a completely different angle."""

def run_query_refiner(state: dict) -> dict:
    response = client.beta.chat.completions.parse(
        model=model_for("refiner"),
        messages=[
            {"role": "system", "content": REFINER_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Original question: {state['question']}\n"
                    f"Already searched: {state['subquestions']}\n"
                    f"Missing information: {state['missing_info']}"
                ),
            },
        ],
        response_format=RefinerOutput,
        temperature=0.2,
    )
    parsed: RefinerOutput = response.choices[0].message.parsed
    state["subquestions"]    = parsed.refined_subquestions
    state["iteration_count"] += 1
    return state
