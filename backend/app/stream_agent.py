"""Streaming agent — yields step dicts as the agent works.

Each yield is one event sent to the frontend via WebSocket.
This replaces the LangGraph-based graph.py for the streaming use-case,
keeping the same sandbox execution underneath.
"""

from __future__ import annotations

import re
from groq import Groq
from app.config import GROQ_API_KEY, LLM_MODEL, MAX_ITERATIONS
from app.exec_tool import execute_code


_client = Groq(api_key=GROQ_API_KEY)

_SYSTEM_PROMPT = """\
You are an autonomous coding agent. You write Python code to complete tasks.

You work in a loop:
1. Write Python code to accomplish the task
2. The code will be executed and you'll see the output
3. If there's an error, fix your code and try again
4. If it works correctly, respond with "TASK COMPLETE" followed by a brief summary

ALWAYS respond with a Python code block like this:
```python
# your code here
```

Or if done:
TASK COMPLETE: <brief summary>

Be concise. Always include print statements to verify output."""


def _extract_code(text: str) -> str | None:
    match = re.search(r"```(?:python|py)?\s*\n?(.*?)```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return None


def run_agent_streaming(task: str):
    """Generator that yields step dicts as the agent works."""

    history = []
    iterations = 0
    final_code = ""

    yield {"type": "start", "task": task}

    while iterations < MAX_ITERATIONS:
        messages = [{"role": "system", "content": _SYSTEM_PROMPT}]
        messages.append({"role": "user", "content": f"Task: {task}"})
        messages.extend(history)

        yield {"type": "thinking", "iteration": iterations + 1}

        response = _client.chat.completions.create(
            model=LLM_MODEL,
            messages=messages,
            temperature=0.1,
            max_tokens=1024,
        )
        content = response.choices[0].message.content

        # Extract code block
        code = _extract_code(content)
        
        if not code:
            # Check if LLM says it's done (must be at the start of a line to avoid false positives)
            if re.search(r"^\s*TASK COMPLETE", content, re.MULTILINE):
                yield {
                    "type": "complete",
                    "message": content,
                    "final_code": final_code,
                    "iterations": iterations + 1,
                }
                return

            history.append({"role": "assistant", "content": content})
            history.append({
                "role": "user",
                "content": "ERROR: No code block found. Please respond with a ```python code block.",
            })
            iterations += 1
            continue

        yield {"type": "code_written", "code": code, "iteration": iterations + 1}

        # Execute in sandbox
        yield {"type": "executing", "iteration": iterations + 1}
        result = execute_code(code)

        stdout = result["output"]
        success = result["success"]

        yield {
            "type": "execution_result",
            "stdout": stdout,
            "success": success,
            "iteration": iterations + 1,
        }

        final_code = code
        history.append({"role": "assistant", "content": content})

        # Build feedback for LLM
        feedback = f"Execution result:\nExit code: {result['exit_code']}\n{stdout}"
        if success:
            feedback += "\n\nThe code ran successfully. If the output is correct, respond with TASK COMPLETE: <summary>. Otherwise, fix any issues."
        history.append({"role": "user", "content": feedback})

        iterations += 1

    yield {"type": "timeout", "iterations": iterations}
