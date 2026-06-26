"""Subprocess fallback runner for Meridian."""

from __future__ import annotations

import subprocess
import tempfile
import os
import shutil

SUBPROCESS_CONFIG = {
    "python":     {"filename": "solution.py",  "cmd": ["python",  "solution.py"]},
    "javascript": {"filename": "solution.js",  "cmd": ["node",    "solution.js"]},
    "bash":       {"filename": "solution.sh",  "cmd": ["bash",    "solution.sh"]},
    # C++ and Java require compilers — not available in subprocess mode
    # Fall back to Python with a clear message for unsupported languages
}

def run_code_subprocess(code: str, language: str = "python") -> dict:
    """Fallback sandbox using subprocess (no Docker needed)."""
    config = SUBPROCESS_CONFIG.get(language)

    if not config:
        return {
            "stdout": "",
            "stderr": (
                f"{language} requires a compiler not available in "
                f"subprocess mode. Install Docker to run {language} code."
            ),
            "exit_code": 1,
            "error": "unsupported_language",
            "language": language,
        }

    tmp_dir = tempfile.mkdtemp()
    file_path = os.path.join(tmp_dir, config["filename"])

    try:
        with open(file_path, "w") as f:
            f.write(code)
        result = subprocess.run(
            config["cmd"],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=tmp_dir,
        )
        return {
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
            "exit_code": result.returncode,
            "error": None,
            "language": language,
        }
    except subprocess.TimeoutExpired:
        return {
            "stdout": "",
            "stderr": "Timeout",
            "exit_code": -1,
            "error": "timeout",
            "language": language,
        }
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
