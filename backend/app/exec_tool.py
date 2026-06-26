"""High-level code execution tool for the Meridian agent."""

from __future__ import annotations

from app.sandbox.docker_runner import run_code_in_sandbox


def execute_code(code: str, language: str = "python") -> dict:
    """Execute code in the sandbox and return a structured result.

    Args:
        code: Source code string.
        language: Programming language to use.

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

    result = run_code_in_sandbox(code, language=language)

    if result.get("error") == "docker_not_available":
        from app.sandbox.subprocess_runner import run_code_subprocess
        result = run_code_subprocess(code, language=language)

    if result.get("error") == "timeout":
        return {
            "output": "ERROR: Execution timed out (30s limit exceeded)",
            "success": False,
            "exit_code": -1,
            "error": "timeout",
        }

    if result.get("error") == "compilation_failed":
        return {
            "output": f"COMPILATION ERROR:\n{result['stderr']}",
            "success": False,
            "exit_code": result.get("exit_code", -1),
            "error": "compilation_failed",
        }

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
