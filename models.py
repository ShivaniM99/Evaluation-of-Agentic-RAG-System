"""Per-node generator model selection.

Every node defaults to OPENAI_CHAT_MODEL. Override one node with ATLAS_MODEL_<NODE>, e.g.

    ATLAS_MODEL_SYNTHESIZER=gpt-4o ATLAS_MODEL_VERIFIER=gpt-4o   # strong model where answers are decided
    (planner / analyzer / refiner keep the cheap default)

Nodes: planner, analyzer, refiner, synthesizer, verifier. Generator models must be OpenAI models
(the nodes use OpenAI structured outputs); only the eval judge can use another provider.
"""
import os

from config import OPENAI_CHAT_MODEL

NODES = ("planner", "analyzer", "refiner", "synthesizer", "verifier")


def model_for(node: str) -> str:
    assert node in NODES, node
    return os.getenv(f"ATLAS_MODEL_{node.upper()}") or OPENAI_CHAT_MODEL


def all_models() -> dict:
    return {n: model_for(n) for n in NODES}
