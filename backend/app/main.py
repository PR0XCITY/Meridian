"""FastAPI app with WebSocket endpoint for streaming agent execution."""

from __future__ import annotations

import json
import os

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app.stream_agent import run_agent_streaming

PORT = int(os.getenv("PORT", 8000))

async def warm_up():
    import docker
    try:
        client = docker.from_env()
    except Exception:
        return
    images_to_pull = [
        "python:3.11-slim",
        "gcc:13-bookworm",
        "node:20-slim",
    ]
    for image in images_to_pull:
        try:
            client.images.get(image)
            print(f"Image already cached: {image}")
        except Exception:
            print(f"Pulling {image} in background...")
            client.images.pull(image)
            print(f"Ready: {image}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    asyncio.create_task(warm_up())
    yield

app = FastAPI(title="Meridian", version="0.1.0", lifespan=lifespan)

allowed_origins = os.getenv("ALLOWED_ORIGINS", "*").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.websocket("/ws/agent")
async def agent_websocket(websocket: WebSocket):
    await websocket.accept()
    try:
        data = await websocket.receive_text()
        payload = json.loads(data)
        task = payload.get("task", "")
        history = payload.get("history", None)

        if not task.strip():
            await websocket.send_text(
                json.dumps({"type": "error", "message": "No task provided"})
            )
            return

        for step in run_agent_streaming(task, previous_history=history):
            await websocket.send_text(json.dumps(step))

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_text(
                json.dumps({"type": "error", "message": str(e)})
            )
        except Exception:
            pass
