import os
import json

# Force the specific remote Database link requested by the user
os.environ["DATABASE_URL"] = env.DATABASE_URL

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.intelligence.clustering import ClusteringEngine
from src.intelligence.temporal import TemporalEngine
from src.intelligence.advanced import AdvancedIntelligenceEngine
from decision_layer import process_decisions
from src.trust_layer import compute_trust_score

def run_pipeline():
    print("--- STARTING END-TO-END MARKET INTELLIGENCE PIPELINE ---")
    
    # 1. Init Database Session using the strict database URL defined above
    engine = create_engine(os.environ["DATABASE_URL"])
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        # ==========================================
        # PHASE 1: INTELLIGENCE LAYER
        # ==========================================
        print("\n[Phase 1] Running Intelligence Layer...")
        
        # 1a. Clustering (Groups incoming competitor signals)
        clust_engine = ClusteringEngine(db)
        print(" -> Ingesting and embedding raw data (if any)...")
        clust_result = clust_engine.run_clustering()
        print(f" -> Clustering result: {clust_result}")
        
        # 1b. Temporal/Trend computations
        print(" -> Calculating Temporal Trends and Saturation...")
        temp_engine = TemporalEngine(db)
        trends = temp_engine.calculate_trends()
        saturations = temp_engine.calculate_saturation()
        
        # 1c. Advanced Intelligence (Whitespace & Persona Drift)
        print(" -> Running Advanced Semantic Analysis (Whitespace/Drift)...")
        adv_engine = AdvancedIntelligenceEngine(db)
        whitespaces = adv_engine.detect_whitespace()
        
        # Consolidate Intelligence outputs to pipe into the Decision Layer
        insights = []
        for t in trends:
            c_id = t["cluster_id"]
            # Find matching saturation mapping
            s_match = next((s for s in saturations if s["cluster_id"] == c_id), None)
            sat_score = s_match["saturation_score"] if s_match else 0.0
            
            # Map detected whitespace vectors into themes (In production handled by LLM, simulated here)
            w_personas = ["budget-conscious", "untapped-niche"] if whitespaces else []
            
            insights.append({
                "cluster_id": c_id,
                "cluster_name": t["cluster_label"] or "Untitled Cluster",
                "trend": t["growth_rate"],
                "saturation": sat_score,
                "whitespace_personas": w_personas
            })
            
        if not insights:
            print(" -> [WARNING] No valid clusters or trends found in the remote database. Ensure signals table is populated.")
            return

        # ==========================================
        # PHASE 2: DECISION LAYER
        # ==========================================
        print("\n[Phase 2] Running Decision Layer...")
        # Pure decoupled logic function imported from decision_layer.py
        decisions = process_decisions(insights)
        print(f" -> Generated {len(decisions)} actionable experiment decisions.")

        # ==========================================
        # PHASE 3: TRUST LAYER
        # ==========================================
        print("\n[Phase 3] Running Trust Layer (Risk & Traceability)...")
        final_experiments = []
        
        for decision in decisions:
            cluster_id = decision["cluster_id"]
            experiment_text = decision["experiment"]
            
            # Execute trust validation using external database signals 
            trust_output = compute_trust_score(
                cluster_id=cluster_id, 
                experiment=experiment_text, 
                client_positioning="premium"
            )
            
            final_experiments.append({
                "cluster_id": cluster_id,
                "cluster_name": decision["cluster_name"],
                "decision": {
                    "priority_label": decision["priority"],
                    "priority_score": decision["priority_score"],
                    "experiment": experiment_text,
                    "counterfactual": decision["counterfactual"]
                },
                "trust_and_risk": trust_output
            })
            
        # ==========================================
        # FINAL OUTPUT PAYLOAD
        # ==========================================
        print("\n=======================================================")
        print("   🚀 FINAL EXPERIMENT BUILDER JSON PAYLOAD 🚀")
        print("=======================================================")
        print(json.dumps(final_experiments, indent=2))
        
    except Exception as e:
        print(f"\n[ERROR] Pipeline failed during execution: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()
        print("\n--- PIPELINE END ---")

if __name__ == "__main__":
    run_pipeline()
