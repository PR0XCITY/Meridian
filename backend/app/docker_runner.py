"""Docker-based sandboxed code execution for Meridian."""

from __future__ import annotations

import docker
from docker.errors import DockerException, ImageNotFound, ContainerError, APIError
from app.config import SANDBOX_IMAGE, SANDBOX_TIMEOUT


def run_code_in_sandbox(code: str) -> dict:
    """Execute Python code inside a Docker container.

    Args:
        code: Python source code to execute.

    Returns:
        dict with keys:
            stdout: captured standard output
            stderr: captured standard error
            exit_code: container exit code (0 = success)
            error: error message if something went wrong at the infra level
    """
    try:
        client = docker.from_env()
    except DockerException as exc:
        return {
            "stdout": "",
            "stderr": str(exc),
            "exit_code": -1,
            "error": f"Docker is not available: {exc}",
        }

    # Ensure the image exists locally
    try:
        client.images.get(SANDBOX_IMAGE)
    except ImageNotFound:
        try:
            client.images.pull(SANDBOX_IMAGE)
        except APIError as exc:
            return {
                "stdout": "",
                "stderr": str(exc),
                "exit_code": -1,
                "error": f"Failed to pull image {SANDBOX_IMAGE}: {exc}",
            }

    container = None
    try:
        container = client.containers.run(
            image=SANDBOX_IMAGE,
            command=["python", "-c", code],
            detach=True,
            mem_limit="256m",
            network_disabled=True,
            stdout=True,
            stderr=True,
        )

        # Wait for execution with timeout
        result = container.wait(timeout=SANDBOX_TIMEOUT)
        exit_code = result.get("StatusCode", -1)

        stdout = container.logs(stdout=True, stderr=False).decode("utf-8", errors="replace")
        stderr = container.logs(stdout=False, stderr=True).decode("utf-8", errors="replace")

        return {
            "stdout": stdout,
            "stderr": stderr,
            "exit_code": exit_code,
            "error": None,
        }

    except Exception as exc:
        return {
            "stdout": "",
            "stderr": str(exc),
            "exit_code": -1,
            "error": f"Sandbox execution error: {exc}",
        }
    finally:
        if container is not None:
            try:
                container.remove(force=True)
            except Exception:
                pass
