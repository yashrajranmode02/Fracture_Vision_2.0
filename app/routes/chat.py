"""
POST /api/chat — Clinical Q&A chatbot using RAG.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.pipeline.rag import retrieve_context, call_groq, extract_json, GROQ_API_KEY
import json

router = APIRouter()

class ChatRequest(BaseModel):
    query: str
    session_id: Optional[str] = None
    groq_api_key: Optional[str] = None

class ChatResponse(BaseModel):
    answer: str

@router.post("/chat", response_model=ChatResponse)
async def chat_with_ai(req: ChatRequest):
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    api_key = req.groq_api_key or GROQ_API_KEY
    if not api_key:
        raise HTTPException(status_code=500, detail="Groq API key not configured")

    try:
        # 1. Retrieve clinical context from FAISS
        # We leverage the existing retrieve_context from our RAG pipeline
        context = retrieve_context(req.query, k=3)

        # 2. Build the specialist prompt (synced with user's chat_with_rag.py)
        prompt = f"""
        You are an AI Clinical Assistant specializing in orthopedic trauma of the forearm.
        Use the following clinical context retrieved from our database to answer the user's question accurately.
        If the context doesn't contain the specific answer, use your medical knowledge to provide a general clinical perspective, but prioritize the database data.

        ### Clinical Context:
        {context}

        ### User Question:
        {req.query}

        ### Response Requirements:
        - Professional and empathetic tone.
        - Mention specific nerves (Radial, Ulnar, Median) or vessels if applicable.
        - Be clear about injury risks.
        - If needed, suggest clinical follow-up like EMG or Doppler.
        - Use bullet points for structural clarity where appropriate.
        - Format your response using Markdown (use bolding for emphasis).
        - **IMPORTANT**: If the user asks for a 'short' or 'concise' response, provide a high-impact summary of maximum 3-4 bullet points and no more than 2-3 sentences of text.
        """

        # 3. Call Groq
        answer = call_groq(prompt, api_key)
        
        return ChatResponse(answer=answer)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat error: {str(e)}")
