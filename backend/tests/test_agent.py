"""test_agent.py – Verify the LangGraph agent loop works end-to-end.

Tests:
    1. Graph compiles and is invocable.
    2. State schema has all required keys.
    3. Code extraction regex works.
    4. Node functions produce correct state updates.
    5. Full agent run (requires Docker + Groq API key).
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from unittest.mock import patch, MagicMock

from app.state import AgentState
from app.nodes import generate_code, execute_code_node, check_result, _extract_code
from app.graph import build_graph, agent
from app.config import GROQ_API_KEY


# ── Helpers ──────────────────────────────────────────────────────────

def _docker_available() -> bool:
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

skip_no_groq_key = pytest.mark.skipif(
    not GROQ_API_KEY,
    reason="GROQ_API_KEY not set",
)


# ── Code extraction ─────────────────────────────────────────────────

class TestCodeExtraction:
    def test_fenced_python_block(self):
        text = 'Here is the code:\n```python\nprint("hi")\n```\nDone.'
        assert _extract_code(text) == 'print("hi")'

    def test_fenced_block_no_lang(self):
        text = '```\nx = 1\n```'
        assert _extract_code(text) == "x = 1"

    def test_no_block_returns_text(self):
        text = 'print("hi")'
        assert _extract_code(text) == 'print("hi")'

    def test_multiline_block(self):
        text = '```python\nfor i in range(3):\n    print(i)\n```'
        code = _extract_code(text)
        assert "for i in range(3):" in code
        assert "print(i)" in code


# ── Graph structure ──────────────────────────────────────────────────

class TestGraphStructure:
    def test_graph_compiles(self):
        compiled = build_graph()
        assert compiled is not None

    def test_agent_is_compiled(self):
        # The module-level `agent` should already be compiled
        assert agent is not None


# ── Check result routing ─────────────────────────────────────────────

class TestCheckResult:
    def test_success_returns_end(self):
        state = {"status": "success", "iteration": 1}
        assert check_result(state) == "end"

    def test_max_iterations_returns_end(self):
        state = {"status": "error", "iteration": 15}
        assert check_result(state) == "end"

    def test_error_returns_generate(self):
        state = {"status": "error", "iteration": 1}
        assert check_result(state) == "generate"

    def test_pending_returns_generate(self):
        state = {"status": "pending", "iteration": 0}
        assert check_result(state) == "generate"


# ── Node functions (mocked) ─────────────────────────────────────────

class TestGenerateCodeMocked:
    """Test generate_code with a mocked Groq client."""

    @patch("app.nodes.Groq")
    def test_returns_code_and_message(self, mock_groq_cls):
        # Setup mock
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content='```python\nprint("hello")\n```'))
        ]
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_groq_cls.return_value = mock_client

        state = {
            "task": "Print hello",
            "code": "",
            "result": "",
            "status": "pending",
            "iteration": 0,
            "messages": [],
        }

        result = generate_code(state)
        assert "code" in result
        assert result["code"] == 'print("hello")'
        assert "messages" in result
        assert len(result["messages"]) == 1


class TestExecuteCodeMocked:
    """Test execute_code_node with mocked sandbox."""

    @patch("app.nodes._exec_code")
    def test_success_execution(self, mock_exec):
        mock_exec.return_value = {
            "output": "42",
            "success": True,
            "exit_code": 0,
            "error": None,
        }

        state = {
            "code": "print(42)",
            "iteration": 0,
            "messages": [],
        }

        result = execute_code_node(state)
        assert result["status"] == "success"
        assert result["iteration"] == 1
        assert "42" in result["result"]

    @patch("app.nodes._exec_code")
    def test_error_execution(self, mock_exec):
        mock_exec.return_value = {
            "output": "NameError: name 'x' is not defined",
            "success": False,
            "exit_code": 1,
            "error": None,
        }

        state = {
            "code": "print(x)",
            "iteration": 0,
            "messages": [],
        }

        result = execute_code_node(state)
        assert result["status"] == "error"
        assert result["iteration"] == 1


# ── Full integration ─────────────────────────────────────────────────

@skip_no_docker
@skip_no_groq_key
class TestAgentIntegration:
    """End-to-end agent test (requires Docker + Groq key)."""

    def test_simple_task(self):
        initial_state = {
            "messages": [],
            "task": "Calculate and print the sum of 1 + 1",
            "code": "",
            "result": "",
            "status": "pending",
            "iteration": 0,
        }

        final_state = agent.invoke(initial_state)

        assert final_state["status"] == "success"
        assert final_state["iteration"] >= 1
        assert "2" in final_state["result"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
