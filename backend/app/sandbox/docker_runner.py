"""Docker-based sandboxed code execution for Meridian."""

from __future__ import annotations

import docker
import tempfile, os, shutil
from app.config import SANDBOX_TIMEOUT

# Configuration for each supported language
LANGUAGE_CONFIG = {
    "python": {
        "image":    "python:3.11-slim",
        "filename": "solution.py",
        "compile":  None,
        "run":      "python /workspace/solution.py",
    },
    "cpp": {
        "image":    "gcc:13-bookworm",
        "filename": "solution.cpp",
        "compile":  "g++ -o /workspace/solution /workspace/solution.cpp",
        "run":      "/workspace/solution",
    },
    "c": {
        "image":    "gcc:13-bookworm",
        "filename": "solution.c",
        "compile":  "gcc -o /workspace/solution /workspace/solution.c",
        "run":      "/workspace/solution",
    },
    "java": {
        "image":    "eclipse-temurin:21-jdk",
        "filename": "Solution.java",
        "compile":  "javac /workspace/Solution.java",
        "run":      "java -cp /workspace Solution",
    },
    "javascript": {
        "image":    "node:20-slim",
        "filename": "solution.js",
        "compile":  None,
        "run":      "node /workspace/solution.js",
    },
    "typescript": {
        "image":    "node:20-slim",
        "filename": "solution.ts",
        "compile":  "npx ts-node /workspace/solution.ts",
        "run":      None,
    },
    "go": {
        "image":    "golang:1.22-bookworm",
        "filename": "solution.go",
        "compile":  None,
        "run":      "go run /workspace/solution.go",
    },
    "rust": {
        "image":    "rust:1.77-slim",
        "filename": "solution.rs",
        "compile":  "rustc /workspace/solution.rs -o /workspace/solution",
        "run":      "/workspace/solution",
    },
    "bash": {
        "image":    "bash:5",
        "filename": "solution.sh",
        "compile":  None,
        "run":      "bash /workspace/solution.sh",
    },
}

def run_code_in_sandbox(code: str, language: str = "python") -> dict:
    """
    Runs code in an isolated Docker container.
    Supports multiple programming languages.
    Returns {stdout, stderr, exit_code, error, language}
    """
    config = LANGUAGE_CONFIG.get(language, LANGUAGE_CONFIG["python"])
    tmp_dir = tempfile.mkdtemp(prefix="meridian_")
    filename = config["filename"]
    file_path = os.path.join(tmp_dir, filename)

    try:
        _client = docker.from_env()
    except Exception as e:
        return {
            "stdout": "",
            "stderr": f"Docker API error: {e}",
            "exit_code": -1,
            "error": "docker_not_available",
            "language": language,
        }

    try:
        with open(file_path, "w") as f:
            f.write(code)

        # Pull image if not present (first run for that language)
        try:
            _client.images.get(config["image"])
        except docker.errors.ImageNotFound:
            print(f"Pulling {config['image']} for first {language} run...")
            _client.images.pull(config["image"])

        # If compilation needed, run compile step first
        if config["compile"]:
            compile_result = _run_container(
                _client,
                image=config["image"],
                command=config["compile"],
                tmp_dir=tmp_dir,
                timeout=60,  # compile timeout
            )
            if compile_result["exit_code"] != 0:
                return {
                    "stdout": "",
                    "stderr": f"Compilation failed:\n{compile_result['stderr']}",
                    "exit_code": compile_result["exit_code"],
                    "error": "compilation_failed",
                    "language": language,
                }

        # Run the program
        if config["run"]:
            result = _run_container(
                _client,
                image=config["image"],
                command=config["run"],
                tmp_dir=tmp_dir,
                timeout=SANDBOX_TIMEOUT,
            )
            result["language"] = language
            return result

        return {
            "stdout": "No run command configured",
            "stderr": "",
            "exit_code": 0,
            "error": None,
            "language": language,
        }

    except Exception as e:
        return {
            "stdout": "",
            "stderr": str(e),
            "exit_code": -1,
            "error": str(e),
            "language": language,
        }
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def _run_container(_client, image: str, command: str, 
                   tmp_dir: str, timeout: int) -> dict:
    """Helper: run a single command in a Docker container."""
    try:
        container = _client.containers.run(
            image=image,
            command=command,
            volumes={tmp_dir: {"bind": "/workspace", "mode": "rw"}},
            working_dir="/workspace",
            mem_limit="256m",
            cpu_quota=50000,
            network_disabled=True,
            detach=True,
            remove=False,
        )
        try:
            result = container.wait(timeout=timeout)
            exit_code = result["StatusCode"]
            stdout = container.logs(
                stdout=True, stderr=False
            ).decode("utf-8", errors="replace").strip()
            stderr = container.logs(
                stdout=False, stderr=True
            ).decode("utf-8", errors="replace").strip()
        except Exception:
            container.kill()
            return {
                "stdout": "",
                "stderr": "Execution timed out",
                "exit_code": -1,
            }
        finally:
            container.remove(force=True)

        return {"stdout": stdout, "stderr": stderr, "exit_code": exit_code}

    except Exception as e:
        return {"stdout": "", "stderr": str(e), "exit_code": -1}
