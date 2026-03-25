import os
import torch
from transformers import pipeline
from src.semantic_search import semantic_search

# Global Model Pipeline for Generative RAG
_generator = None
# Utilizing an ultra-lightweight (0.5B), highly-capable local Instruct model
MODEL_NAME = "Qwen/Qwen2.5-0.5B-Instruct"

def get_generator():
    """Builds and caches the local HuggingFace generation pipeline."""
    global _generator
    if _generator is None:
        print(f"Loading local generative LLM '{MODEL_NAME}'...")
        print("This might take a minute initially to download the weights (~1GB).")
        
        # Default to CPU execution unless a CUDA GPU is available
        device = 0 if torch.cuda.is_available() else -1
        
        _generator = pipeline(
            "text-generation",
            model=MODEL_NAME,
            torch_dtype=torch.float32 if device == -1 else torch.float16,
            device=device
        )
    return _generator

def chat_with_experiment(experiment_text: str, user_query: str, chat_history: list = None) -> str:
    """
    Acts as a completely offline Market Intelligence Copilot using an open-source LLM.
    Uses RAG (Retrieval-Augmented Generation) against the PostgreSQL signal_embeddings table.
    
    Args:
        experiment_text (str): The chosen experiment strategy that is the focal point.
        user_query (str): The primary question the user is asking.
        chat_history (list): Previous conversation history mapping [{"role": "user"/"assistant", "content": "..."}]
        
    Returns:
        str: The generated clarification response.
    """
    if chat_history is None:
        chat_history = []

    generator = get_generator()

    # 1. Context Augmentation (RAG)
    search_query = f"{experiment_text} {user_query}"
    try:
        # Fetching top 3 signals to keep prompt memory context size slim for a small local model
        search_results = semantic_search(search_query, top_k=3)
        signals = search_results.get("results", [])
    except Exception as e:
        print(f"Warning: Failed to retrieve semantic context: {e}")
        signals = []

    # Format the retrieved signals into a readable context block
    context_blocks = []
    for i, s in enumerate(signals, 1):
        content = s.get('content', '')
        context_blocks.append(f"- {content}")
    
    context_text = "\n".join(context_blocks) if context_blocks else "No relevant background signals found in the database."

    # 2. System Prompt Assembly
    system_prompt = f"""You are a Market Intelligence Execution Copilot.
Your primary role is to help the user understand, clarify, and execute the following successfully proposed experiment.

CHOSEN EXPERIMENT STRATEGY TO EXECUTE:
"{experiment_text}"

RETRIEVED MARKET SIGNALS (Vector Database Context):
{context_text}

INSTRUCTIONS:
1. Answer the user's questions strictly regarding the chosen experiment above.
2. Use the retrieved market signals to justify your answers.
3. Keep your responses concise and analytical. Do not hallucinate data that isn't provided in the given context.
"""

    messages = [{"role": "system", "content": system_prompt}]
    
    # 3. Append history and current query
    for msg in chat_history:
        if "role" in msg and "content" in msg:
            messages.append(msg)
            
    messages.append({"role": "user", "content": user_query})

    # Apply the specific chat tokens/templates native to the model automatically (e.g. ChatML for Qwen)
    prompt = generator.tokenizer.apply_chat_template(
        messages, 
        tokenize=False, 
        add_generation_prompt=True
    )

    # 4. Local LLM Generation (Offline Inference)
    outputs = generator(
        prompt,
        max_new_tokens=300,
        do_sample=True,
        temperature=0.3,
        return_full_text=False # Only returns the newly generated assistant text portion
    )

    return outputs[0]["generated_text"].strip()
