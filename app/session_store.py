"""
In-memory session store + SSE event queue per session.
"""
import asyncio
import uuid
from typing import Dict, Any, Optional

# session_id -> session dict
sessions: Dict[str, Dict[str, Any]] = {}

# session_id -> list of SSE event dicts waiting to be sent
progress_queues: Dict[str, asyncio.Queue] = {}


def create_session() -> str:
    session_id = str(uuid.uuid4())
    sessions[session_id] = {
        "xray_image": None,         # numpy array
        "xray_filename": None,
        "landmarks": None,          # dict of centered coords
        "fracture_data": None,      # list of fracture dicts
        "risk_result": None,        # Groq risk analysis result
        "output_glb_path": None,    # path to final .glb
        "status": "created",        # created | processing | done | error
    }
    progress_queues[session_id] = asyncio.Queue()
    return session_id


def get_session(session_id: str) -> Optional[Dict[str, Any]]:
    return sessions.get(session_id)


async def push_progress(session_id: str, step: int, total: int, message: str, status: str = "running"):
    """Push a progress event to the SSE queue for this session."""
    if session_id in progress_queues:
        await progress_queues[session_id].put({
            "step": step,
            "total": total,
            "message": message,
            "status": status,
        })


async def push_done(session_id: str):
    await push_progress(session_id, 7, 7, "Pipeline complete", "done")


async def push_error(session_id: str, message: str):
    await push_progress(session_id, -1, 7, f"Error: {message}", "error")
