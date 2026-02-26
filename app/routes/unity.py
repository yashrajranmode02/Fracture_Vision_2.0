from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from app.supabase_client import _get_client
from pydantic import BaseModel
import uuid

router = APIRouter(prefix="/unity", tags=["unity"])

class UnityHistoryItem(BaseModel):
    session_id: str
    report_name: str
    created_at: str
    xray_url: Optional[str]

class UnityReport(BaseModel):
    report_name: str
    created_at: str
    summary: Optional[str]
    model_url: str
    landmarks: dict
    risks: List[dict]

@router.get("/history", response_model=List[UnityHistoryItem])
async def get_unity_history(email: str = Query(..., description="User email to fetch history for")):
    """
    Fetch history for a specific email. 
    In a production app, you might want to add a secret API key or similar.
    """
    supabase = _get_client()
    
    # 1. Get user_id for this email
    user_res = supabase.table("users").select("id").eq("email", email).execute()
    if not user_res.data:
        return []
        
    user_id = user_res.data[0]["id"]
    
    # 2. Get reports for this user
    reports_res = supabase.table("reports").select("session_id, report_name, created_at, xray_url").eq("user_id", user_id).order("created_at", desc=True).execute()
    
    return [
        UnityHistoryItem(
            session_id=str(r["session_id"]),
            report_name=r["report_name"] or "Untitled Case",
            created_at=r["created_at"],
            xray_url=r["xray_url"]
        ) for r in reports_res.data
    ]

@router.get("/report/{session_id}", response_model=UnityReport)
async def get_unity_report(session_id: str):
    """
    Fetch full report data and model URL for a specific session.
    """
    supabase = _get_client()
    
    res = supabase.table("reports").select("*").eq("session_id", session_id).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Report not found")
        
    report = res.data[0]
    risk_data = report.get("risk_result") or {}
    
    return UnityReport(
        report_name=report.get("report_name") or "Untitled Case",
        created_at=report["created_at"],
        summary=risk_data.get("summary") or "No summary available",
        model_url=report["model_url"] or "",
        landmarks=report.get("landmarks") or {},
        risks=risk_data.get("damaged_structures") or []
    )
