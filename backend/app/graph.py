"""LangGraph state graph wiring for the Meridian coding agent.

Session 1 graph topology:

    START ──▶ generate_code ──▶ execute_code ──▶ check_result
                 ▲                                     │
                 │              "generate"              │
                 └─────────────────────────────────────┘
                                "end" ──▶ END
"""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from app.nodes import check_result, execute_code_node, generate_code
from app.state import AgentState


def build_graph() -> StateGraph:
    """Construct and compile the Session 1 agent graph."""

    graph = StateGraph(AgentState)

    # Register nodes
    graph.add_node("generate_code", generate_code)
    graph.add_node("execute_code", execute_code_node)

    # Edges
    graph.add_edge(START, "generate_code")
    graph.add_edge("generate_code", "execute_code")

    # Conditional routing after execution
    graph.add_conditional_edges(
        "execute_code",
        check_result,
        {
            "generate": "generate_code",
            "end": END,
        },
    )

    return graph.compile()


# Module-level compiled graph for import convenience
agent = build_graph()
