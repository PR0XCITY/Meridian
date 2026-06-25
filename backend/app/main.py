"""FastAPI app with WebSocket endpoint for streaming agent execution."""

from __future__ import annotations

import json

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app.stream_agent import run_agent_streaming

app = FastAPI(title="Meridian", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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

        if not task.strip():
            await websocket.send_text(
                json.dumps({"type": "error", "message": "No task provided"})
            )
            return

        for step in run_agent_streaming(task):
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
