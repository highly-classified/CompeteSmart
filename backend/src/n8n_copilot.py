import os
import httpx
from typing import List, Dict, Optional
from dotenv import load_dotenv

load_dotenv()

def chat_with_n8n(user_query: str, chat_history: list = None, session_id: str = None) -> dict:
    """
    Communicates with the n8n CompeteSmart Experiment Suggestion Chatbot webhook.
    """
    webhook_url = os.environ.get("N8N_WEBHOOK_URL")
    
    if not webhook_url:
        return {
            "success": False,
            "reply": "Error: N8N_WEBHOOK_URL not set in environment.",
            "topic": "error"
        }

    if chat_history is None:
        chat_history = []

    payload = {
        "message": user_query,
        "sessionId": session_id or "default_session",
        "history": chat_history
    }

    try:
        with httpx.Client(timeout=35.0) as client:
            response = client.post(webhook_url, json=payload)
            response.raise_for_status()
            return response.json()
    except httpx.TimeoutException:
        return {
            "success": False,
            "reply": "The n8n workflow timed out. Please check if the workflow is active.",
            "topic": "error"
        }
    except Exception as e:
        return {
            "success": False,
            "reply": f"Connection Error: {str(e)}",
            "topic": "error"
        }
