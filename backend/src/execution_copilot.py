import os
from typing import List, Dict, Optional
from src.semantic_search import semantic_search
from src.trust_layer import compute_trust_score
from dotenv import load_dotenv

load_dotenv()

def chat_with_experiment(experiment_text: str, user_query: str, chat_history: list = None, cluster_id: str = None) -> str:
    """
    Acts as a Market Intelligence Execution Strategy Consultant using Gemini 3.1 Flash-Lite.
    Provides deep implementation handbooks and instant tactical answers.
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
    system_instruction = f"""You are the CompeteSmart Execution Strategy Consultant, an elite AI specialized in operationalizing market intelligence.
Your goal is to provide the user with a "COMPLETE IMPLEMENTATION HANDBOOK" for their chosen experiment and answer follow-up logistics questions with instant, tactical precision.

CHOSEN EXPERIMENT:
"{experiment_text}"

{trust_context}

RELEVANT MARKET SIGNALS:
{context_signals}

OPERATIONAL GUIDELINES:
1. INITIAL HANDBOOK: If the user has just started the session or selected an experiment, output a comprehensive implementation guide with THESE EXACT HEADERS:
   - ## 🎯 Executive Summary: Why this works based on market signals.
   - ## 🗺️ Tactical Roadmap: A clear Phase 1, 2, and 3 timeline.
   - ## 🛠️ Resource Requirements: What tools, data, or team skills are needed.
   - ## 📈 KPI Tracking: Exactly which metrics to monitor to measure success.
   - ## ⚠️ Risk Mitigation: Specific actions to avoid based on the Trust Layer Analysis.

2. INSTANT FOLLOW-UPS: For any subsequent questions, provide immediate, specific, and actionable advice. Refer back to the relevant phase (Phase 1, 2, or 3) of the handbook you just generated if necessary. Do not repeat the whole handbook; focus only on the user's specific query.

3. STYLE: Use professional, authoritative language. Use bolding and structured lists for readability. Always justify your tactical advice using the 'RELEVANT MARKET SIGNALS' provided.

4. BREADTH: If the user asks about the 'CompeteSmart' tool itself, explain that we use real-time web scraping, vector embeddings (pgvector), and LLM-driven clustering to identify these opportunities.
"""

    # 3. Gemini Chat Initialization
    try:
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            import google.generativeai as genai
            
        api_key = os.environ.get("GEMINI_API_KEY")
        if api_key:
            genai.configure(api_key=api_key)
        else:
            print("Warning: GEMINI_API_KEY not found in environment.")
            
        # Using the ultra-fast 3.1 Flash-Lite model with dedicated system instructions
        model = genai.GenerativeModel(
            model_name='models/gemini-3.1-flash-lite-preview',
            system_instruction=system_instruction
        )
        
        # Convert history format to Gemini's format
        gemini_history = []
        for msg in chat_history:
            role = "user" if msg["role"] == "user" else "model"
            gemini_history.append({"parts": [{"text": msg["content"]}], "role": role})

        # Start chat with history
        chat = model.start_chat(history=gemini_history)
        
        # Send only the user query, as the system instruction is already set in the model
        response = chat.send_message(user_query)
        return response.text
    except Exception as e:
        return f"Gemini Implementation Error: {str(e)}"
