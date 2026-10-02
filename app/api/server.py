"""Local HTTP and event-stream API for the Revelio prototype UI."""

import os
import json
import queue
import threading
from typing import Any

import uvicorn

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.main import run
from app.services.document_parser import DocumentParser

app = FastAPI(title="Revelio local API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


class InvestigationRequest(BaseModel):
    goal: str = Field(min_length=1, max_length=4000)


MAX_UPLOAD_COUNT = 3
MAX_FILE_BYTES = 10 * 1024 * 1024
MAX_TOTAL_UPLOAD_BYTES = 25 * 1024 * 1024


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/investigate")
def investigate(request: InvestigationRequest) -> StreamingResponse:
    """Run one goal and stream structured progress events as SSE."""
    return _stream_investigation(request.goal.strip())


@app.post("/api/investigate-with-documents")
async def investigate_with_documents(
    goal: str = Form(min_length=1, max_length=4000),
    files: list[UploadFile] = File(...),
) -> StreamingResponse:
    """Run an investigation using up to three in-memory document uploads."""
    if not files or len(files) > MAX_UPLOAD_COUNT:
        raise HTTPException(status_code=400, detail=f"Upload between 1 and {MAX_UPLOAD_COUNT} documents.")

    parser = DocumentParser()
    documents = []
    total_bytes = 0
    for index, upload in enumerate(files, start=1):
        try:
            content = await upload.read(MAX_FILE_BYTES + 1)
            total_bytes += len(content)
            if len(content) > MAX_FILE_BYTES:
                raise HTTPException(status_code=413, detail=f"{upload.filename or 'A file'} exceeds the 10 MB limit.")
            if total_bytes > MAX_TOTAL_UPLOAD_BYTES:
                raise HTTPException(status_code=413, detail="Combined uploads exceed the 25 MB limit.")
            try:
                document = parser.parse_upload(upload.filename or "document", content)
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
            documents.append(document.model_copy(update={"url": f"upload://{index}/{document.title}"}))
        finally:
            await upload.close()
    return _stream_investigation(goal.strip(), documents)


def _stream_investigation(goal: str, documents=None) -> StreamingResponse:
    events: queue.Queue[dict[str, Any] | None] = queue.Queue()

    def worker() -> None:
        try:
            state = run(goal, on_event=events.put, documents=documents)
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


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="127.0.0.1", port=port)
