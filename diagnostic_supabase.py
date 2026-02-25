import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")

if not url or not key:
    print("ERROR: SUPABASE_URL or SUPABASE_KEY missing in .env")
    exit(1)

supabase: Client = create_client(url, key)

print(f"--- Supabase Diagnostic ---")
print(f"URL: {url}")

print("\n1. Checking 'reports' table...")
try:
    res = supabase.table("reports").select("*").limit(1).execute()
    print("SUCCESS: 'reports' table is accessible.")
except Exception as e:
    print(f"FAILURE: Cannot access 'reports' table.")
    print(f"DEBUG ERROR: {type(e).__name__}: {e}")
    print("HINT: Make sure you ran the SQL command to create the table.")

print("\n2. Checking 'fractures' bucket...")
try:
    buckets = supabase.storage.list_buckets()
    bucket_names = [b.name for b in buckets]
    if "fractures" in bucket_names:
        print("SUCCESS: 'fractures' bucket exists.")
    else:
        print(f"FAILURE: 'fractures' bucket not found. Existing buckets: {bucket_names}")
        print("HINT: Please create a bucket named 'fractures' in Supabase Storage.")
except Exception as e:
    print(f"FAILURE: Cannot list buckets. Error: {e}")

print("\n--- Diagnostic End ---")
