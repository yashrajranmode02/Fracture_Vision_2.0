"""
RAG retrieval + Groq LLM risk analysis.
"""
import json
import os
import requests
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

# Fallback to creds.json - check both local and root dirs
if not GROQ_API_KEY:
    possible_creds = [
        os.path.join(os.getcwd(), "creds.json"),
        os.path.join(os.path.dirname(__file__), "..", "..", "creds.json"),
        "creds.json"
    ]
    for cp in possible_creds:
        if os.path.exists(cp):
            try:
                with open(cp, "r") as f:
                    data = json.load(f)
                    GROQ_API_KEY = data.get("api_key") or data.get("GROQ_API_KEY")
                    if GROQ_API_KEY:
                        print(f"[RAG] Successfully loaded key from {cp}")
                        break
            except Exception as e:
                print(f"[RAG] Error reading {cp}: {e}")
GROQ_MODEL = "llama-3.3-70b-versatile"

BASE_DIR = os.path.join(os.path.dirname(__file__), "..", "..")
FAISS_INDEX_PATH = os.path.join(BASE_DIR, "forearm_index.faiss")
DOCUMENTS_JSON_PATH = os.path.join(BASE_DIR, "documents.json")

_rag_cache = None


def get_rag():
    global _rag_cache
    if _rag_cache is None:
        embedder = SentenceTransformer("all-MiniLM-L6-v2")
        index = faiss.read_index(os.path.abspath(FAISS_INDEX_PATH))
        with open(os.path.abspath(DOCUMENTS_JSON_PATH), "r", encoding="utf-8") as f:
            documents = json.load(f)
        _rag_cache = (embedder, index, documents)
    return _rag_cache


def retrieve_context(fracture_list, k=5):
    embedder, index, documents = get_rag()
    query = json.dumps(fracture_list)
    vector = embedder.encode([query]).astype("float32")
    _, I = index.search(vector, k)
    return "\n\n".join(documents[i] for i in I[0])


def build_prompt(context, fracture_list):
    fracture_json = json.dumps(fracture_list, indent=2)
    return f"""
You are a senior orthopedic trauma specialist AI analyzing forearm fractures.

The data is derived from 2D X-ray analysis.
Depth information is NOT available.
You must infer displacement risk using location and angulation only.

### Context:
{context}

### Fracture Data:
{fracture_json}

### Clinical Reasoning Requirements:
Use advanced anatomical reasoning including:
- Proximity of neurovascular bundles to fracture site
- Effect of angulation differences (top vs bottom angle)
- Biomechanical instability from bilateral bone involvement
- Risk of vessel compression from fragment displacement
- Risk of nerve entrapment due to angular deformity
- Compartment pressure risk if applicable

### Task:
1. Identify blood vessels and nerves at risk.
2. Estimate probability of damage (0.0 to 1.0).
3. Always return AT LEAST 3 structures.
4. Prefer structures with probability >= 0.4.
5. If fewer than 3 exceed 0.4, still include top 3 highest risks.
6. Sort by probability descending.

### Output Format (STRICT JSON ONLY):
{{
  "damaged_structures": [
    {{
      "name": "structure name",
      "probability": 0.00
    }}
  ],
  "summary": "Concise clinical summary (2-4 high-impact sentences) explaining anatomical risk, biomechanical implications, and key neurovascular pathways."
}}

### Rules:
- Minimum 3 structures required
- Summary must be CONCISE (3-5 sentences)
- Valid JSON only
- No markdown
- No extra commentary
- Double quotes only
- Probabilities must be between 0.0 and 1.0
"""


def call_groq(prompt: str, api_key: str) -> str:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": "You are a clinical fracture risk assistant."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.1,
    }
    response = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers=headers, json=payload, timeout=60
    )
    data = response.json()
    if "choices" not in data:
        raise RuntimeError(f"Groq API Error: {data}")
    return data["choices"][0]["message"]["content"].strip()


def extract_json(text: str) -> str:
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("No JSON found in LLM output")
    return text[start:end + 1]


def validate_output(result: dict) -> dict:
    structures = result.get("damaged_structures", [])
    valid = []
    for s in structures:
        prob = float(np.clip(float(s.get("probability", 0)), 0.0, 1.0))
        valid.append({"name": s.get("name", "unknown"), "probability": round(prob, 2)})
    valid.sort(key=lambda x: x["probability"], reverse=True)
    if len(valid) < 3:
        raise ValueError("LLM returned fewer than 3 structures")
    result["damaged_structures"] = valid
    return result


def analyze_fracture_risk(fracture_list: list, api_key: str = None) -> dict:
    key = api_key or GROQ_API_KEY
    print(f"[RAG] Analysis starting. Key available: {bool(key)}")
    if not key:
        raise ValueError("No Groq API key available in .env or creds.json")
    
    context = retrieve_context(fracture_list)
    print(f"[RAG] Context retrieved. Length: {len(context)}")
    
    prompt = build_prompt(context, fracture_list)
    raw = call_groq(prompt, key)
    result = json.loads(extract_json(raw))
    return validate_output(result)
