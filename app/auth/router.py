import os
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.supabase_client import supabase

bearer_scheme = HTTPBearer(auto_error=False)
router = APIRouter()

def _get_current_user(creds: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme)):
    if creds is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    if not supabase:
        # Fallback for local dev if supabase isn't configured, though we should expect it
        return {"email": "dev@example.com", "name": "Developer"}

    try:
        # Verify the token with Supabase
        user_res = supabase.auth.get_user(creds.credentials)
        if not user_res or not user_res.user:
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        
        user = user_res.user
        return {
            "id": user.id,
            "email": user.email,
            "name": user.user_metadata.get("name", "User")
        }
    except Exception as e:
        print(f"[Auth] Token verification error: {e}")
        raise HTTPException(status_code=401, detail="Authentication failed")

@router.get("/me")
def me(user=Depends(_get_current_user)):
    return user
