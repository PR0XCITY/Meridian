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

_SYSTEM_PROMPT = """You are an autonomous coding agent. You write 
code in whatever programming language the user requests.

LANGUAGE DETECTION RULES:
- If the user mentions a specific language (Python, C++, Java, 
  JavaScript, Go, Rust, C, etc.), use EXACTLY that language
- If no language is mentioned, default to Python
- NEVER switch languages mid-task

You work in a loop:
1. Write code in the requested language to accomplish the task
2. The code will be executed and you will see the output
3. If there is an error, fix your code and try again
4. If it works correctly, respond with TASK COMPLETE followed 
   by a brief summary

ALWAYS respond with a code block using the correct language tag:
For Python:     ```python
For C++:        ```cpp
For Java:       ```java
For JavaScript: ```javascript
For Go:         ```go
For Rust:       ```rust
For C:          ```c
For Bash:       ```bash

Note: For Java, the public class must always be named "Solution".

Or if the task is done:
TASK COMPLETE: <brief summary>

Be concise. Always include print/output statements so you can 
verify the output. Write complete, compilable/runnable code."""

LANGUAGE_MAP = {
    "python":     "python",
    "py":         "python",
    "cpp":        "cpp",
    "c++":        "cpp",
    "cxx":        "cpp",
    "java":       "java",
    "javascript": "javascript",
    "js":         "javascript",
    "typescript": "typescript",
    "ts":         "typescript",
    "go":         "go",
    "golang":     "go",
    "rust":       "rust",
    "rs":         "rust",
    "c":          "c",
    "bash":       "bash",
    "sh":         "bash",
    "shell":      "bash",
}

def _extract_code(text: str) -> tuple[str | None, str]:
    """
    Extract code block from LLM response.
    Returns (code, language) tuple.
    Language defaults to 'python' if not detected.
    """
    match = re.search(r"```(\w+)?\n(.*?)```", text, re.DOTALL)
    if match:
        lang_raw = (match.group(1) or "python").lower().strip()
        code = match.group(2).strip()
        language = LANGUAGE_MAP.get(lang_raw, "python")
        return code, language

    # Fallback: plain ``` block with no language tag
    match = re.search(r"```\n(.*?)```", text, re.DOTALL)
    if match:
        return match.group(1).strip(), "python"

    return None, "python"


def _build_system_prompt() -> str:
    return _SYSTEM_PROMPT


# ─── nodes ───────────────────────────────────────────────────────────

def generate_code(state: AgentState) -> dict:
    """Call Groq LLM to generate (or refine) code for the task."""

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
            # For this node, we'll just use a generic code block if we don't have the language in state.
            # But we can extract it from the last AI message.
            last_lang = "python"
            if state.get("messages"):
                for m in reversed(state["messages"]):
                    if isinstance(m, AIMessage):
                        _, last_lang = _extract_code(m.content)
                        break
            
            groq_messages.append(
                {
                    "role": "assistant",
                    "content": f"```{last_lang}\n{state['code']}\n```",
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
                        f"code block."
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
    code, language = _extract_code(llm_text)

    # Since we can't add `language` to `AgentState` directly, we just store `code`
    # and we can re-extract `language` from `llm_text` inside `execute_code_node`.
    return {
        "code": code,
        "messages": [AIMessage(content=llm_text)],
    }


def execute_code_node(state: AgentState) -> dict:
    """Run the generated code in the Docker sandbox."""

    code = state.get("code", "")
    
    # Extract language from the most recent AIMessage in state["messages"]
    language = "python"
    if state.get("messages"):
        for m in reversed(state["messages"]):
            if isinstance(m, AIMessage):
                _, language = _extract_code(m.content)
                break

    result = _exec_code(code, language=language)

    new_status = "success" if result["success"] else "error"
    new_iteration = state.get("iteration", 0) + 1

    return {
        "result": result["output"],
        "status": new_status,
        "iteration": new_iteration,
        "messages": [
            HumanMessage(
                content=f"[sandbox iteration={new_iteration} language={language}] "
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
