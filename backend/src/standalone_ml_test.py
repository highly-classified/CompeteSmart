import json
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
import os

def standalone_ml_test():
    print("--- COMPETE SMART: STANDALONE ML EXPERIMENT RANKER ---")
    
    # 1. LOAD EXISTING DATA
    data_path = "decision_layer_output.json"
    if not os.path.exists(data_path):
        print(f"Error: {data_path} not found. Please run the pipeline first.")
        return

    with open(data_path, 'r') as f:
        raw_data = json.load(f)

    print(f"Loaded {len(raw_data)} insights from existing data.")

    # 2. FEATURE ENGINEERING
    # Extract numerical features from the raw data for the ML model
    processed_data = []
    for item in raw_data:
        # We simulate features that an ML model would use
        # In a real scenario, these would come from the database 'trends' table
        try:
            # Parse momentum from the insight string (heuristic fallback)
            momentum_str = item['insight'].split('with ')[1].split('%')[0]
            momentum = float(momentum_str) / 100.0
        except:
            momentum = 0.0

        processed_data.append({
            "cluster_id": item['cluster_id'],
            "cluster_name": item['insight'].split("'")[1] if "'" in item['insight'] else "General",
            "momentum": momentum,
            "risk": item['risk'],
            "confidence": item['confidence'],
            "evidence_count": len(item['evidence']),
            "recommended_action": item['recommended_action']
        })

    df = pd.DataFrame(processed_data)

    # 3. DEFINE STRATEGIC TARGET (THE "TEACHER")
    # For this POC, we define a Custom Success Score that the model will learn.
    # High Momentum + Low Risk + High Evidence = High Success Probability.
    df['success_score'] = (
        (df['momentum'] * 0.5) + 
        ((1.0 - df['risk']) * 0.3) + 
        (np.log1p(df['evidence_count']) * 0.2)
    )

    # 4. TRAIN THE ML MODEL
    features = ['momentum', 'risk', 'confidence', 'evidence_count']
    X = df[features]
    y = df['success_score']

    # Scale features
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # Train a Random Forest Regressor
    model = RandomForestRegressor(n_estimators=100, random_state=42)
    model.fit(X_scaled, y)

    print("ML Model (RandomForest) trained on existing data characteristics.")

    # 5. PREDICT AND RANK
    df['ml_predicted_score'] = model.predict(X_scaled)
    
    # Sort by ML score and get Top 3
    top_3 = df.sort_values(by='ml_predicted_score', ascending=False).head(3)

    # 6. OUTPUT RESULTS
    print("\n" + "="*50)
    print("TOP 3 STRATEGIC EXPERIMENTS (ML RECOMMENDED)")
    print("="*50)
    
    for i, (idx, row) in enumerate(top_3.iterrows(), 1):
        print(f"\n{i}. INSIGHT: {row['cluster_name']}")
        print(f"   ACTION: {row['recommended_action']}")
        print(f"   ML CONFIDENCE SCORE: {row['ml_predicted_score']:.4f}")
        print(f"   FEATURES: Momentum: {row['momentum']*100:.1f}%, Risk: {row['risk']:.2f}, Evidence: {row['evidence_count']}")

    # Save to a separate results file
    output_results = top_3[['cluster_name', 'recommended_action', 'ml_predicted_score']].to_dict(orient='records')
    with open('ml_standalone_results.json', 'w') as f:
        json.dump(output_results, f, indent=2)
    
    print("\nResults saved to ml_standalone_results.json")

if __name__ == "__main__":
    standalone_ml_test()
