"""
POST /api/upload — Accept X-ray image, return session_id + base64 preview.
"""
import base64
import cv2
import numpy as np
from fastapi import APIRouter, File, UploadFile, HTTPException

from app.session_store import create_session, sessions

router = APIRouter()


@router.post("/upload")
async def upload_xray(file: UploadFile = File(...), report_name: str = "New Analysis"):
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image files are accepted")

    contents = await file.read()
    nparr = np.frombuffer(contents, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if img is None:
        raise HTTPException(status_code=400, detail="Could not decode image")

    # Scale to 50% like the CLI pipeline
    scale = 0.5
    h, w = img.shape[:2]
    resized = cv2.resize(img, (int(w * scale), int(h * scale)))

    session_id = create_session()
    sessions[session_id]["xray_image"] = resized
    sessions[session_id]["xray_filename"] = file.filename
    sessions[session_id]["report_name"] = report_name

    _, buffer = cv2.imencode(".jpg", resized)
    img_b64 = base64.b64encode(buffer).decode("utf-8")

    return {
        "session_id": session_id,
        "image_base64": f"data:image/jpeg;base64,{img_b64}",
        "width": resized.shape[1],
        "height": resized.shape[0],
    }
