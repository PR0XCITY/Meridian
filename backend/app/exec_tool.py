"""High-level code execution tool for the Meridian agent."""

from __future__ import annotations

from app.docker_runner import run_code_in_sandbox


def execute_code(code: str) -> dict:
    """Execute code in the sandbox and return a structured result.

    Args:
        code: Python source code string.

    Returns:
        dict with keys:
            output: combined stdout + stderr for display
            success: True if exit_code == 0
            exit_code: raw exit code
            error: infrastructure error message or None
    """
    if not code or not code.strip():
        return {
            "output": "No code provided.",
            "success": False,
            "exit_code": -1,
            "error": "Empty code string",
        }

    result = run_code_in_sandbox(code)

    # Combine output for agent consumption
    parts = []
    if result["stdout"]:
        parts.append(result["stdout"])
    if result["stderr"]:
        parts.append(result["stderr"])

    combined = "\n".join(parts) if parts else "(no output)"

    return {
        "output": combined,
        "success": result["exit_code"] == 0,
        "exit_code": result["exit_code"],
        "error": result.get("error"),
    }
