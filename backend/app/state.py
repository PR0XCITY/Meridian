"""Agent state definition for the Meridian coding agent."""

from __future__ import annotations

from typing import Annotated, TypedDict
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    """State that flows through the LangGraph agent loop.

    Attributes:
        messages: Conversation history (uses add_messages reducer for append).
        task: The original user task / problem statement.
        code: The latest generated code from the LLM.
        result: Stdout/stderr from the sandbox execution.
        status: "pending" | "success" | "error".
        iteration: Current iteration count.
    """

    messages: Annotated[list, add_messages]
    task: str
    code: str
    result: str
    status: str
    iteration: int
