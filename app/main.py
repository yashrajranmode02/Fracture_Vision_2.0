"""
FractureVision — FastAPI Backend
Run: uvicorn app.main:app --reload --port 8000
"""
import os
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.routes.upload import router as upload_router
from app.routes.landmarks import router as landmarks_router
from app.routes.progress import router as progress_router
from app.routes.model import router as model_router
from app.routes.chat import router as chat_router
from app.routes.unity import router as unity_router
from app.auth.router import router as auth_router
from app.auth.router import _get_current_user

app = FastAPI(
    title="FractureVision API",
    description="AI-powered forearm fracture detection and 3D visualization",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount output files as static (for serving .glb and annotated images)
outputs_dir = os.path.join(os.path.dirname(__file__), "..", "outputs")
os.makedirs(outputs_dir, exist_ok=True)

app.include_router(upload_router, prefix="/api")
app.include_router(landmarks_router, prefix="/api")
app.include_router(progress_router, prefix="/api")
app.include_router(model_router, prefix="/api")
app.include_router(chat_router, prefix="/api")
app.include_router(unity_router, prefix="/api")
app.include_router(auth_router, prefix="/api/auth")


@app.get("/")
def root():
    return {
        "service": "FractureVision API",
        "version": "2.0.0",
        "docs": "/docs",
    }


@app.get("/health")
def health():
    return {"status": "ok"}
