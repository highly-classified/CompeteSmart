import os
import google.generativeai as genai
from typing import List, Dict, Optional
from src.semantic_search import semantic_search
from src.trust_layer import compute_trust_score
from dotenv import load_dotenv

load_dotenv()

# Configure Gemini
api_key = os.environ.get("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)
else:
    print("Warning: GEMINI_API_KEY not found in environment.")

def chat_with_experiment(experiment_text: str, user_query: str, chat_history: list = None, cluster_id: str = None) -> str:
    """
    Acts as a Market Intelligence Execution Copilot using Gemini Pro.
    Provides step-by-step curated flows based on market signals and trust layer data.
    """
    if chat_history is None:
        chat_history = []

    # 1. Gather Context
    # A. Search results (Market Signals)
    search_query = f"{experiment_text} {user_query}"
    try:
        search_results = semantic_search(search_query, top_k=5)
        signals = search_results.get("results", [])
    except Exception as e:
        print(f"Warning: Failed to retrieve semantic context: {e}")
        signals = []

    context_signals = "\n".join([f"- {s.get('content', '')}" for s in signals]) if signals else "No relevant market signals found."

    # B. Trust Layer Data
    trust_context = ""
    if cluster_id:
        try:
            # We assume 'premium' as default positioning for this intelligence loop context
            trust_data = compute_trust_score(cluster_id, experiment_text, "premium")
            trust_context = f"""
TRUST LAYER ANALYSIS:
- Risk Score: {trust_data['risk_score']} ({trust_data['risk_level']} risk)
- Expert Explanation: {trust_data['explanation']}
- Supporting Signals Count: {trust_data['traceability']['total_signals']}
"""
        except Exception as e:
            print(f"Warning: Failed to fetch trust data: {e}")

    # 2. System Prompt
    system_instruction = f"""You are the CompeteSmart Execution Copilot, an elite market strategy AI.
Your goal is to turn market intelligence into a step-by-step execution plan for the user.

CHOSEN EXPERIMENT:
"{experiment_text}"

{trust_context}

RELEVANT MARKET SIGNALS:
{context_signals}

OPERATIONAL GUIDELINES:
1. If the user has just selected an experiment (or if this is the start of the discussion for it), provide a "STEP-BY-STEP CURATED FLOW" on how to carry it out.
2. The flow must be tactical, including:
   - Phase 1: Setup & Data Baseline
   - Phase 2: Messaging/Pricing Deployment
   - Phase 3: Monitoring & Pivot Points
3. Integrate the 'Market Signals' to justify specific steps.
4. Use the 'Trust Layer Analysis' to flag risks they must avoid during execution.
5. Keep responses structured (use bolding, bullet points, and clear headers).
6. After the step-by-step guide, invite the user to ask specific questions about the logistics or risks.
7. Be concise but extremely insightful.
"""

    # 3. Gemini Chat Initialization
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        # Convert history format to Gemini's format
        gemini_history = []
        for msg in chat_history:
            role = "user" if msg["role"] == "user" else "model"
            gemini_history.append({"parts": [{"text": msg["content"]}], "role": role})

        # Prepend system instruction as the first turn or instruction
        # (Gemini 1.5 prefers it in the system_instruction parameter or as first message)
        chat = model.start_chat(history=gemini_history)
        
        full_query = f"{system_instruction}\n\nUSER QUERY:\n{user_query}"
        
        response = chat.send_message(full_query)
        return response.text
    except Exception as e:
        return f"Gemini Error: {str(e)}"
