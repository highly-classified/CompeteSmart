import os
import json
import logging
from sqlalchemy.orm import Session
from src.database import SessionLocal
from src import models
from src.ml_decision_layer import process_decisions_ml
from src.cache_manager import refresh_dashboard_cache

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("refresh_ml")

def refresh_ml_results():
    logger.info("Starting manual ML results refresh...")
    
    # 1. Load the most recent insights/clusters to process
    # For the sake of this POC, we'll use the existing decision_layer_output.json 
    # to reconstruct what the pipeline would have sent.
    json_path = "decision_layer_output.json"
    if not os.path.exists(json_path):
        logger.error("No input data found at decision_layer_output.json")
        return

    with open(json_path, "r") as f:
        raw_results = json.load(f)
    
    # Reconstruct the 'insights' format expected by process_decisions_ml
    insights = []
    for r in raw_results:
        # Mocking the insight features
        insights.append({
            "cluster_id": r["cluster_id"],
            "cluster_name": r["insight"].split("'")[1] if "'" in r["insight"] else "Service",
            "trend": 0.96 if "High Priority" in r["trend"] else 0.36 if "Medium" in r["trend"] else 0.1,
            "saturation": r["risk"] / 0.8, # crude reverse mapping
            "evidence": r["evidence"],
            "whitespace_personas": ["budget-conscious"]
        })

    # 2. Run the ML Decision Layer
    logger.info(f"Processing {len(insights)} insight clusters through ML Model...")
    ml_output = process_decisions_ml(insights)
    
    # 3. Update the Database Cache
    db: Session = SessionLocal()
    try:
        # Update suggested_experiments
        cache_key = "suggested_experiments"
        cache_entry = db.query(models.DashboardCache).filter(models.DashboardCache.key == cache_key).first()
        
        if not cache_entry:
            cache_entry = models.DashboardCache(key=cache_key)
            db.add(cache_entry)
            
        cache_entry.value = json.dumps(ml_output[:3]) # Only Top 3 as requested
        db.commit()
        logger.info("Successfully updated DashboardCache with Top 3 ML experiments.")
        
    except Exception as e:
        logger.error(f"Failed to update cache: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    refresh_ml_results()
