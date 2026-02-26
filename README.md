# FractureVision Clinical Diagnostic System

FractureVision is a high-fidelity 3D fracture analysis platform that transforms standard 2D X-rays into interactive clinical models. Designed for orthopaedic surgeons and diagnostic specialists.

## Technical Architecture

-   **Backend**: FastAPI (Python) with SSE for real-time analysis streaming.
-   **Frontend**: Vite + React, styled with a glassmorphic design system.
-   **AI Pipeline**: Custom ML models for landmark detection, bone segmentation, and mesh reconstruction.
-   **Persistence**: Supabase (PostgreSQL + Storage) and Auth.
-   **Integration**: Seamless compatibility with Unity 3D via specialized REST APIs.

## API Endpoints for Unity

The platform provides dedicated routes for external 3D engine integration:

### 1. Fetch History by Email
**Endpoint**: `GET /api/unity/history?email={email}`

**Sample JSON Output**:
```json
[
  {
    "session_id": "f81d4fae-7dec-11d0-a765-00a0c91e6bf6",
    "report_name": "Distal Radius Fracture - Case A",
    "created_at": "2026-02-26T10:00:00Z",
    "xray_url": "https://supabase-url.com/storage/v1/object/public/fractures/users/uuid/session/xray.jpg"
  }
]
```

### 2. Fetch Full Clinical Data
**Endpoint**: `GET /api/unity/report/{session_id}`

**Sample JSON Output**:
```json
{
  "report_name": "Distal Radius Fracture - Case A",
  "created_at": "2026-02-26T10:00:00Z",
  "summary": "Impacted distal radius fracture with 15-degree dorsal tilt.",
  "model_url": "https://supabase-url.com/storage/v1/object/public/fractures/users/uuid/session/model.glb",
  "landmarks": {
    "radius head": [120, 350],
    "ulna head": [130, 345],
    "radius tail": [110, 800],
    "ulna tail": [125, 790]
  },
  "risks": [
    {
      "name": "Osteoarthritis",
      "level": "Moderate",
      "percentage": 45
    },
    {
      "name": "Nerve Compression",
      "level": "Low",
      "percentage": 10
    }
  ]
}
```

## Core Features

-   **Clinical History**: Side-by-side diagnostic list with horizontal "chat-style" aesthetics.
-   **RAG Chatbot**: Integrated clinical specialist AI for fracture-specific Q&A.
-   **Account Management**: Secure user registration, email verification, and profile customization.
-   **Encryption**: JWT-based session security and Supabase RLS policies.

---

*Precision Orthopaedic Intelligence.*
