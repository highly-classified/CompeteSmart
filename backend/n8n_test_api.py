import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional
from src.n8n_copilot import chat_with_n8n
import uvicorn

app = FastAPI(title="CompeteSmart n8n Chatbot Test API")

# Add CORS so the frontend can call this from localhost:3000
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For testing, open to all
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str
    history: Optional[List[Dict[str, str]]] = []
    sessionId: Optional[str] = None

@app.post("/api/n8n/chat")
async def n8n_chat(request: ChatRequest):
    """
    Endpoint for testing the n8n experiment suggestion chatbot.
    """
    try:
        response = chat_with_n8n(
            user_query=request.message,
            chat_history=request.history,
            session_id=request.sessionId
        )
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
def health():
    return {"status": "ok", "message": "n8n test api is running"}

if __name__ == "__main__":
    print("Starting n8n Test API on http://localhost:8001")
    uvicorn.run(app, host="0.0.0.0", port=8001)
