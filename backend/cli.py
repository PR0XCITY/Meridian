"""Meridian Session 1 – CLI entry point.

Usage:
    python main.py                          # interactive prompt
    python main.py "calculate fibonacci"    # direct task
"""

import sys
from app.graph import agent


def run(task: str) -> None:
    """Run the agent loop on a given task and print results."""

    print(f"\n{'='*60}")
    print(f"  Meridian Agent - Session 1")
    print(f"{'='*60}")
    print(f"  Task: {task}\n")

    initial_state = {
        "messages": [],
        "task": task,
        "code": "",
        "result": "",
        "status": "pending",
        "iteration": 0,
    }

    final_state = agent.invoke(initial_state)

    print(f"\n{'-'*60}")
    print(f"  Status:     {final_state['status']}")
    print(f"  Iterations: {final_state['iteration']}")
    print(f"{'-'*60}")
    print(f"  Generated Code:\n")
    print(final_state.get("code", "(none)"))
    print(f"\n{'-'*60}")
    print(f"  Execution Output:\n")
    print(final_state.get("result", "(none)"))
    print(f"{'='*60}\n")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        task = " ".join(sys.argv[1:])
    else:
        task = input("Enter a coding task: ").strip()
        if not task:
            print("No task provided. Exiting.")
            sys.exit(1)

    run(task)
