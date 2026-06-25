"""test_sandbox.py – Verify Docker sandbox execution works end-to-end.

Tests:
    1. A simple print statement executes and returns stdout.
    2. A syntax error produces a non-zero exit code.
    3. An empty code string is handled gracefully.
"""

import sys
import os

# Ensure the backend directory is on sys.path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from app.exec_tool import execute_code
from app.docker_runner import run_code_in_sandbox


def _docker_available() -> bool:
    """Check whether Docker daemon is reachable."""
    try:
        import docker
        client = docker.from_env()
        client.ping()
        return True
    except Exception:
        return False


skip_no_docker = pytest.mark.skipif(
    not _docker_available(),
    reason="Docker daemon is not running",
)


# ── Unit tests (no Docker required) ─────────────────────────────────

class TestExecToolUnit:
    """Tests that don't require Docker (input validation, etc.)."""

    def test_empty_code_returns_error(self):
        result = execute_code("")
        assert result["success"] is False
        assert result["error"] is not None

    def test_whitespace_only_returns_error(self):
        result = execute_code("   \n  ")
        assert result["success"] is False


# ── Integration tests (Docker required) ─────────────────────────────

@skip_no_docker
class TestSandboxIntegration:
    """Integration tests that run code in the Docker sandbox."""

    def test_hello_world(self):
        result = execute_code('print("Hello from sandbox")')
        assert result["success"] is True
        assert "Hello from sandbox" in result["output"]

    def test_arithmetic(self):
        result = execute_code("print(2 + 2)")
        assert result["success"] is True
        assert "4" in result["output"]

    def test_syntax_error(self):
        result = execute_code("def foo(")
        assert result["success"] is False
        assert result["exit_code"] != 0

    def test_multiline_code(self):
        code = "for i in range(3):\n    print(i)"
        result = execute_code(code)
        assert result["success"] is True
        assert "0" in result["output"]
        assert "2" in result["output"]

    def test_import_standard_lib(self):
        code = "import json; print(json.dumps({'a': 1}))"
        result = execute_code(code)
        assert result["success"] is True
        assert '"a"' in result["output"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
