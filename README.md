# 🤖 Meridian — Autonomous Coding Agent

> An autonomous AI coding agent that writes code, executes it in an isolated Docker sandbox, reads the output, debugs failures, and iterates until the task succeeds — with a live streaming web UI showing every reasoning step in real time.

![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=flat&logo=python&logoColor=white)
![LangGraph](https://img.shields.io/badge/LangGraph-Agent_Orchestration-FF6B35?style=flat)
![Docker](https://img.shields.io/badge/Docker-Sandbox-2496ED?style=flat&logo=docker&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-WebSocket-009688?style=flat&logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-18-61DAFB?style=flat&logo=react&logoColor=black)
![Groq](https://img.shields.io/badge/Groq-DeepSeek_R1-F55036?style=flat)
![License](https://img.shields.io/badge/License-MIT-22D3EE?style=flat)

---

## What It Does

Meridian takes a natural language task description and autonomously completes it by:

1. **Reasoning** about the task and writing Python code
2. **Executing** the code in an isolated Docker container (sandboxed — no network, memory-capped)
3. **Observing** stdout, stderr, and exit code
4. **Deciding** — if it worked, declare success; if it failed, read the error and fix the code
5. **Repeating** until the task is complete or the iteration limit is hit

Every step streams live to a web UI showing the agent's reasoning, generated code with syntax highlighting, execution results, and final output.

---

## Demo

```
Task: "Write a binary search implementation and test it with 5 different inputs"

→ Iteration 1:
  [THINKING] I need to implement binary search recursively...
  [CODE WRITTEN] def binary_search(arr, target, low=0, high=None)...
  [EXECUTING] Running in Docker sandbox...
  [RESULT] Exit code: 0 | Found 42 at index 7 ✓

→ TASK COMPLETE in 1 iteration
```

```
Task: "Read data.txt and compute word frequency"

→ Iteration 1:
  [CODE WRITTEN] with open('data.txt') as f...
  [RESULT] Exit code: 1 | FileNotFoundError: data.txt not found

→ Iteration 2:
  [THINKING] File doesn't exist. I should handle this gracefully...
  [CODE WRITTEN] try/except with default message...
  [RESULT] Exit code: 0 ✓

→ TASK COMPLETE in 2 iterations (self-corrected)
```

---

## Architecture

```
User submits task via browser
         │
         ▼ WebSocket connection
┌────────────────────────────────────────────┐
│         FastAPI WebSocket Server           │
└────────────────────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────────┐
│         LangGraph Agent Graph              │
│                                            │
│  ┌──────────┐    ┌──────────┐             │
│  │ Planner  │───▶│ Executor │             │
│  │  (LLM)   │    │  Node    │             │
│  └──────────┘    └──────────┘             │
│        ▲               │                  │
│        │         ┌─────▼──────┐           │
│        │         │  Tool Call │           │
│        │         │ run_code() │           │
│        │         └─────┬──────┘           │
│        │               │                  │
│        │    ┌──────────▼──────────┐       │
│        │    │   Docker Sandbox    │       │
│        │    │  python:3.11-slim   │       │
│        │    │  - No network       │       │
│        │    │  - 256MB RAM cap    │       │
│        │    │  - 30s timeout      │       │
│        │    └──────────┬──────────┘       │
│        │               │ stdout/stderr    │
│        └───────────────┘ (observation)   │
│                                            │
│  Repeats up to 15 iterations               │
└────────────────────────────────────────────┘
         │ streams each step via WebSocket
         ▼
┌────────────────────────────────────────────┐
│           React Streaming UI               │
│  - Live agent reasoning trace              │
│  - Syntax-highlighted code blocks         │
│  - Execution output (green/red)           │
│  - Iteration counter                       │
│  - Session history sidebar                 │
└────────────────────────────────────────────┘
```

---

## Tech Stack

| Component | Technology |
|---|---|
| Agent Framework | LangGraph (stateful graph, ReAct pattern) |
| LLM | Groq — DeepSeek-R1 / Llama-3.3-70B |
| Code Execution | Docker (`python:3.11-slim`, sandboxed) |
| Backend | FastAPI + WebSockets |
| Frontend | React + Vite |
| Streaming | WebSocket (real-time step events) |
| Session Storage | SQLite (task history + agent steps) |
| Syntax Highlight | Custom regex-based Python highlighter |

---

## Project Structure

```
meridian/
├── backend/
│   ├── app/
│   │   ├── agent/
│   │   │   ├── graph.py         # LangGraph state graph definition
│   │   │   ├── nodes.py         # Planner, executor, evaluator nodes
│   │   │   ├── state.py         # AgentState TypedDict
│   │   │   ├── stream_graph.py  # Streaming generator for WebSocket
│   │   │   └── tools/
│   │   │       └── exec_tool.py # run_code() tool
│   │   ├── sandbox/
│   │   │   └── docker_runner.py # Docker subprocess isolation
│   │   ├── config.py
│   │   └── main.py              # FastAPI + WebSocket endpoint
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   └── App.jsx              # Full UI — streaming agent trace
│   └── package.json
├── docker-compose.yml
└── README.md
```

---

## Run Locally

**Prerequisites:** Python 3.11+, Node.js 18+, Docker Desktop

```bash
# Pull the sandbox image first (one time)
docker pull python:3.11-slim

# Backend
cd backend
python -m venv venv
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

pip install -r requirements.txt
cp .env.example .env
# Add GROQ_API_KEY to .env
uvicorn app.main:app --reload --port 8000
```

```bash
# Frontend (new terminal)
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173` → type any coding task → watch the agent work.

**Environment variables:**
```
GROQ_API_KEY=your_groq_api_key
```

---

## Sample Tasks to Try

```
Print the first 20 prime numbers using the Sieve of Eratosthenes
```
```
Implement a stack data structure with push, pop, peek, and is_empty methods. Test all operations.
```
```
Write a function that detects if a string is a palindrome, ignoring spaces and case. Test with 5 examples.
```
```
Connect to a SQLite database, create a users table, insert 5 records, and print all rows sorted by name.
```
```
Implement merge sort and demonstrate it sorting a list of 10 random numbers, showing each merge step.
```

---

## Security Design

Code execution is fully sandboxed per task:

| Constraint | Implementation |
|---|---|
| Network isolation | `network_disabled=True` in Docker |
| Memory limit | `mem_limit="256m"` |
| CPU limit | `cpu_quota=50000` (~50% of one core) |
| Execution timeout | 30 seconds, then container killed |
| Filesystem isolation | Temporary directory mounted per task, deleted after |
| No persistent state | Each task gets a clean container |

**The agent cannot access the internet, your filesystem, or any external resources.**

---

## Agent Loop Technical Details

The ReAct (Reason + Act + Observe) loop:

```
State: { task, history, iterations, final_code, status }

Loop:
  1. LLM receives: system_prompt + task + full history
  2. LLM outputs: either ```python code``` OR "TASK COMPLETE: ..."
  3. If code: extract → run in Docker → append (code + result) to history
  4. If complete: set status="success" → end
  5. If iterations >= 15: set status="timeout" → end
  6. Each step yielded via generator → WebSocket → React UI
```

---

## Key Engineering Decisions

**Why LangGraph over a simple loop?**
LangGraph provides a typed state machine with conditional edges — making the agent's control flow explicit, debuggable, and extensible. Adding new tools or decision nodes is a graph edit, not a refactor.

**Why Docker over subprocess isolation?**
Docker provides true OS-level isolation. The agent's generated code cannot access the host filesystem, network, or other processes. A malicious or buggy script is contained to its container.

**Why stream each step via WebSocket?**
An agent that takes 30 seconds and shows nothing is a broken UX. Streaming every step (thinking, code written, executing, result) makes the reasoning transparent and the tool feel intelligent rather than frozen.

**Why DeepSeek-R1 on Groq?**
DeepSeek-R1 is a reasoning-optimized model that performs well on code generation tasks. Groq's inference speed (300+ tok/s) keeps iteration latency low — critical when the agent may run 5+ LLM calls per task.

---

## What I Learned

- Agent loops require hard iteration limits and timeout handling from day one — without them, runaway agents burn API credits
- Docker container startup adds ~1-2s per iteration — acceptable for demos, but a production system would use pre-warmed containers
- Streaming intermediate steps is not optional for agentic UIs — users need to see the agent "thinking" or they assume it crashed
- LangGraph's `Annotated[list, operator.add]` pattern for history is the correct way to accumulate state across graph nodes

---

## License

MIT — free to use, modify, and distribute.
