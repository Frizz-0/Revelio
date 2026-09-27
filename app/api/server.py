"""Local HTTP and event-stream API for the Revelio prototype UI."""

import json
import queue
import threading
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.main import run

app = FastAPI(title="Revelio local API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


class InvestigationRequest(BaseModel):
    goal: str = Field(min_length=1, max_length=4000)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/investigate")
def investigate(request: InvestigationRequest) -> StreamingResponse:
    """Run one goal and stream structured progress events as SSE."""
    events: queue.Queue[dict[str, Any] | None] = queue.Queue()

    def worker() -> None:
        try:
            state = run(request.goal.strip(), on_event=events.put)
            events.put({"event": "result", "state": state.model_dump(mode="json")})
        except Exception as exc:
            events.put({"event": "failed", "error": str(exc)})
        finally:
            events.put(None)

    def stream():
        thread = threading.Thread(target=worker, daemon=True)
        thread.start()
        while True:
            event = events.get()
            if event is None:
                break
            yield f"data: {json.dumps(event, ensure_ascii=False, default=str)}\n\n"
        thread.join()

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
