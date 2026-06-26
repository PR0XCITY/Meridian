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


def run_agent_streaming(task: str, previous_history: list | None = None):
    """Generator that yields step dicts as the agent works."""

    history = previous_history or []
    history.append({"role": "user", "content": f"Task: {task}"})
    iterations = 0
    final_code = ""

    yield {"type": "start", "task": task}

    while iterations < MAX_ITERATIONS:
        messages = [{"role": "system", "content": _SYSTEM_PROMPT}]
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
        code, language = _extract_code(content)
        
        if not code:
            # Check if LLM says it's done (must be at the start of a line to avoid false positives)
            if re.search(r"^\s*TASK COMPLETE", content, re.MULTILINE):
                yield {
                    "type": "complete",
                    "message": content,
                    "final_code": final_code,
                    "iterations": iterations + 1,
                    "history": history,
                }
                return

            history.append({"role": "assistant", "content": content})
            history.append({
                "role": "user",
                "content": "ERROR: No code block found. Please respond with a ```<language> code block.",
            })
            iterations += 1
            continue

        yield {"type": "code_written", "code": code, "language": language, "iteration": iterations + 1}

        # Execute in sandbox
        yield {"type": "executing", "iteration": iterations + 1}
        result = execute_code(code, language=language)

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
        feedback = f"Language: {language}\nExecution result:\nExit code: {result['exit_code']}\n{stdout}"
        if success:
            feedback += "\n\nThe code ran successfully. If the output is correct, respond with TASK COMPLETE: <summary>. Otherwise, fix any issues."
        history.append({"role": "user", "content": feedback})

        iterations += 1

    yield {"type": "timeout", "iterations": iterations, "history": history}
