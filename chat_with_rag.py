import os
import json
import requests
import faiss
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv

# Load configuration
load_dotenv()
FAISS_INDEX = "forearm_index.faiss"
DOCUMENTS_JSON = "documents.json"
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

if not GROQ_API_KEY and os.path.exists("creds.json"):
    try:
        with open("creds.json", "r") as f:
            GROQ_API_KEY = json.load(f).get("api_key")
    except:
        pass

GROQ_MODEL = "llama-3.3-70b-versatile"

def load_rag():
    print("\033[94m[System] Initializing Clinical Knowledge Base...\033[0m")
    embedder = SentenceTransformer("all-MiniLM-L6-v2")
    index = faiss.read_index(FAISS_INDEX)
    with open(DOCUMENTS_JSON, "r", encoding="utf-8") as f:
        documents = json.load(f)
    print("\033[92m[System] Knowledge Base Ready. You can now ask questions about forearm fractures and risks.\033[0m")
    return embedder, index, documents

def get_answer(query, embedder, index, documents):
    # Retrieve context
    vector = embedder.encode([query]).astype("float32")
    _, I = index.search(vector, 3)
    context = "\n\n".join([documents[i] for i in I[0]])

    # Build prompt
    prompt = f"""
    You are an AI Clinical Assistant specializing in orthopedic trauma of the forearm.
    Use the following clinical context retrieved from our database to answer the user's question accurately.
    If the context doesn't contain the specific answer, use your medical knowledge to provide a general clinical perspective, but prioritize the database data.

    ### Clinical Context:
    {context}

    ### User Question:
    {query}

    ### Response Requirements:
    - Professional and empathetic tone.
    - Mention specific nerves (Radial, Ulnar, Median) or vessels if applicable.
    - Be clear about injury risks.
    - If needed, suggest clinical follow-up like EMG or Doppler.
    """

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": "You are a clinical fracture risk assistant."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
    }

    try:
        response = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=30)
        return response.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        return f"Error connecting to AI service: {e}"

def main():
    if not GROQ_API_KEY:
        print("\033[91m[Error] GROQ_API_KEY not found. Please set it in .env or creds.json\033[0m")
        return

    embedder, index, documents = load_rag()
    
    print("\n" + "="*50)
    print("      FOREARM FRACTURE CLINICAL CHATBOT")
    print("="*50)
    print("Type your question below (e.g., 'What is the risk to the ulnar nerve in a distal fracture?')")
    print("Type 'exit' to quit.\n")

    while True:
        user_input = input("\033[96mUser:\033[0m ").strip()
        
        if user_input.lower() in ['exit', 'quit', 'bye']:
            print("\033[92m[System] Session ended. stay safe!\033[0m")
            break
        
        if not user_input:
            continue

        print("\033[93m[Thinking...]\033[0m", end="\r")
        answer = get_answer(user_input, embedder, index, documents)
        print(" "*20, end="\r") # Clear thinking line
        print(f"\033[95mAssistant:\033[0m\n{answer}\n")

if name == "main":
    main()