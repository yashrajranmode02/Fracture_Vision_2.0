import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")

if not url or not key:
    print("[Supabase] WARNING: SUPABASE_URL or SUPABASE_KEY not found in environment")
    supabase: Client = None
else:
    supabase: Client = create_client(url, key)

def _get_client(jwt_token: str = None) -> Client:
    if not supabase:
        return None
    if not jwt_token:
        return supabase
    
    # Create a fresh client for this request to be thread-safe with RLS
    # This avoids modifying the global 'supabase' client's headers
    scoped_client = create_client(url, key)
    scoped_client.postgrest.auth(jwt_token)
    # For storage, we need to update the headers on the session
    if hasattr(scoped_client.storage, 'session'):
        scoped_client.storage.session.headers.update({"Authorization": f"Bearer {jwt_token}"})
    return scoped_client

def save_report_to_supabase(data: dict, jwt_token: str = None):
    client = _get_client(jwt_token)
    if not client:
        print("[Supabase] Error: Client not initialized")
        return None
    
    try:
        print(f"[Supabase] Attempting to save report for session {data.get('session_id')}")
        response = client.table("reports").insert(data).execute()
        if hasattr(response, 'data') and response.data:
            print(f"[Supabase] Save success: {response.data}")
            return response.data
        else:
            print(f"[Supabase] Save returned no data: {response}")
            return None
    except Exception as e:
        print(f"[Supabase] CRITICAL Error saving report: {type(e).__name__} - {e}")
        # Try to print response body if it's a PostgrestError
        if hasattr(e, 'message'):
            print(f"[Supabase] Error message: {e.message}")
        return None

def upload_file_to_supabase(file_path: str, bucket: str, destination_path: str, jwt_token: str = None):
    client = _get_client(jwt_token)
    if not client:
        print("[Supabase] Error: Client not initialized")
        return None
    
    try:
        print(f"[Supabase] Uploading {file_path} to {bucket}/{destination_path}")
        if not os.path.exists(file_path):
            print(f"[Supabase] Error: Local file not found: {file_path}")
            return None
            
        with open(file_path, "rb") as f:
            response = client.storage.from_(bucket).upload(
                path=destination_path,
                file=f,
                file_options={"upsert": "true"}
            )
        
        # Get public URL
        res = client.storage.from_(bucket).get_public_url(destination_path)
        print(f"[Supabase] Upload success. Public URL: {res}")
        return res
    except Exception as e:
        print(f"[Supabase] CRITICAL Error uploading file {file_path}: {e}")
        return None

def get_reports_from_supabase(user_id: str = None, jwt_token: str = None):
    client = _get_client(jwt_token)
    if not client:
        return []
    try:
        print(f"[Supabase] Fetching report history{' for user ' + user_id if user_id else ''}...")
        query = client.table("reports").select("*").order("created_at", desc=True)
        if user_id:
            query = query.eq("user_id", user_id)
        response = query.execute()
        print(f"[Supabase] Fetched {len(response.data)} reports")
        return response.data
    except Exception as e:
        print(f"[Supabase] CRITICAL Error fetching reports: {e}")
        return []

def get_report_by_session(session_id: str):
    if not supabase:
        return None
    try:
        print(f"[Supabase] Fetching report for session {session_id}")
        response = supabase.table("reports").select("*").eq("session_id", session_id).single().execute()
        return response.data
    except Exception as e:
        print(f"[Supabase] Error fetching report {session_id}: {e}")
        return None
