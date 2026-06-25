"""LangGraph node functions for the Meridian coding agent.

Nodes:
    generate_code  – Calls Groq LLM to produce Python code for the task.
    execute_code   – Runs the generated code in the Docker sandbox.
    check_result   – Decides whether to loop or finish (routing function).
"""

from __future__ import annotations

import re

from groq import Groq
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.config import GROQ_API_KEY, LLM_MODEL, MAX_ITERATIONS
from app.exec_tool import execute_code as _exec_code
from app.state import AgentState


# ─── helpers ─────────────────────────────────────────────────────────

_CODE_BLOCK_RE = re.compile(r"```(?:python|py)?\s*\n?(.*?)```", re.DOTALL)


def _extract_code(text: str) -> str:
    """Extract the first Python code block from LLM output.

    Falls back to the entire text if no fenced block is found.
    """
    match = _CODE_BLOCK_RE.search(text)
    if match:
        return match.group(1).strip()
    # If no code block markers, treat the whole response as code
    return text.strip()


def _build_system_prompt() -> str:
    return (
        "You are Meridian, an expert Python coding assistant. "
        "When the user gives you a task, respond ONLY with a Python code "
        "block (```python ... ```) that solves the task. "
        "Do NOT include any explanation outside the code block. "
        "The code will be executed in a sandbox. "
        "Print the final result to stdout."
    )


# ─── nodes ───────────────────────────────────────────────────────────

def generate_code(state: AgentState) -> dict:
    """Call Groq LLM to generate (or refine) Python code for the task."""

    client = Groq(api_key=GROQ_API_KEY)

    # Build message list for the API
    groq_messages = [{"role": "system", "content": _build_system_prompt()}]

    # On first iteration, send the task.  On subsequent iterations, include
    # the prior code + execution result so the LLM can fix errors.
    if state.get("iteration", 0) == 0:
        groq_messages.append({"role": "user", "content": state["task"]})
    else:
        groq_messages.append({"role": "user", "content": state["task"]})
        if state.get("code"):
            groq_messages.append(
                {
                    "role": "assistant",
                    "content": f"```python\n{state['code']}\n```",
                }
            )
        if state.get("result"):
            groq_messages.append(
                {
                    "role": "user",
                    "content": (
                        f"The code produced the following output/error:\n"
                        f"```\n{state['result']}\n```\n"
                        f"Please fix the code and respond with a corrected "
                        f"Python code block."
                    ),
                }
            )

    response = client.chat.completions.create(
        model=LLM_MODEL,
        messages=groq_messages,
        temperature=0.0,
        max_tokens=4096,
    )

    llm_text = response.choices[0].message.content
    code = _extract_code(llm_text)

    return {
        "code": code,
        "messages": [AIMessage(content=llm_text)],
    }


def execute_code_node(state: AgentState) -> dict:
    """Run the generated code in the Docker sandbox."""

    code = state.get("code", "")
    result = _exec_code(code)

    new_status = "success" if result["success"] else "error"
    new_iteration = state.get("iteration", 0) + 1

    return {
        "result": result["output"],
        "status": new_status,
        "iteration": new_iteration,
        "messages": [
            HumanMessage(
                content=f"[sandbox iteration={new_iteration}] "
                        f"exit_code={result['exit_code']}\n{result['output']}"
            )
        ],
    }


# ─── routing (conditional edge) ──────────────────────────────────────

def check_result(state: AgentState) -> str:
    """Decide the next node: 'end' if success or max iterations, else 'generate'."""

    if state.get("status") == "success":
        return "end"
    if state.get("iteration", 0) >= MAX_ITERATIONS:
        return "end"
    return "generate"
