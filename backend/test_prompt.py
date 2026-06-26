import sys
from app.stream_agent import run_agent_streaming

def run_test(prompt):
    print(f"\n--- Testing: {prompt} ---")
    for step in run_agent_streaming(prompt):
        if step["type"] == "code_written":
            print(f"Code written ({step.get('language', 'unknown')}):\n{step['code'][:100]}...")
        elif step["type"] == "execution_result":
            print(f"Execution success: {step['success']}")
            print(f"Stdout:\n{step['stdout']}")
        elif step["type"] == "complete":
            print(f"Completed after {step['iterations']} iterations")
            return
        elif step["type"] == "error":
            print(f"Error: {step.get('message')}")
        elif step["type"] == "timeout":
            print("Timed out.")

if __name__ == "__main__":
    prompts = [
        "Print fibonacci sequence up to 10 terms",
        "Print prime numbers till 20 in C++",
        "Write a function to reverse a string in JavaScript and test it",
    ]
    for p in prompts:
        run_test(p)
