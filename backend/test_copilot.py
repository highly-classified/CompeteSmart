from src.execution_copilot import chat_with_experiment

def run_test():
    experiment_text = "Launch a premium tier focused on verified professionals to compete with established platforms."
    user_query = "What exactly are the risks of this strategy, based on the market signals?"
    
    print("--- Running Execution Copilot RAG ---")
    print(f"Chosen Experiment: {experiment_text}")
    print(f"User Query: {user_query}\n")
    print("Generating response from GPT (this might take a few seconds)...\n")
    
    try:
        response = chat_with_experiment(experiment_text, user_query)
        print("--- Copilot Response ---")
        print(response)
    except Exception as e:
        print(f"Failed to generate response: {e}")

if __name__ == "__main__":
    run_test()
