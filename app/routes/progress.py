"""
GET /api/progress/{session_id} — SSE stream of pipeline step updates.
"""
import json
import asyncio
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from app.session_store import progress_queues

router = APIRouter()


@router.get("/progress/{session_id}")
async def stream_progress(session_id: str):
    async def event_generator():
        if session_id not in progress_queues:
            yield f"data: {json.dumps({'status': 'error', 'message': 'Session not found'})}\n\n"
            return

        queue = progress_queues[session_id]
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=60.0)
                yield f"data: {json.dumps(event)}\n\n"
                if event.get("status") in ("done", "error"):
                    break
            except asyncio.TimeoutError:
                # Heartbeat to keep connection alive
                yield ": heartbeat\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
