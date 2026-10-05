# agent_graph.py
from langgraph.graph import StateGraph, END
from typing import TypedDict
from nodes.planner import run_planner
from nodes.retriever import run_retriever
from nodes.analyzer import run_analyzer
from nodes.query_refiner import run_query_refiner
from nodes.synthesizer import run_synthesizer
from config import MAX_ITERATIONS
from index_loader import LoadedIndex


class AgentState(TypedDict):
    question: str
    intent: str
    subquestions: list[str]
    retrieved_chunks: list[dict]
    evidence_sufficient: bool
    missing_info: str
    iteration_count: int
    draft_answer: str
    final_answer: str
    uncertainty_flag: bool

def build_agent(index: LoadedIndex):
    graph = StateGraph(AgentState)

    graph.add_node("planner",        lambda s: run_planner(s))
    graph.add_node("retriever",      lambda s: run_retriever(s, index))
    graph.add_node("analyzer",       lambda s: run_analyzer(s))
    graph.add_node("query_refiner",  lambda s: run_query_refiner(s))
    graph.add_node("synthesizer",    lambda s: run_synthesizer(s))

    graph.set_entry_point("planner")
    graph.add_edge("planner",   "retriever")
    graph.add_edge("retriever", "analyzer")

    def route_after_analyzer(state: AgentState) -> str:
        if state["evidence_sufficient"] or state["iteration_count"] >= MAX_ITERATIONS:
            return "synthesizer"
        return "query_refiner"

    graph.add_conditional_edges("analyzer", route_after_analyzer, {
        "synthesizer":  "synthesizer",
        "query_refiner": "query_refiner",
    })
    graph.add_edge("query_refiner", "retriever")
    graph.add_edge("synthesizer",   END)

    return graph.compile()