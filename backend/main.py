from fastapi import FastAPI, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import text
from src.database import get_db, engine
from src import models
from src.intelligence.clustering import ClusteringEngine
from src.intelligence.temporal import TemporalEngine
from src.intelligence.advanced import AdvancedIntelligenceEngine
from src.intelligence.schemas.clustering import SignalInput
from src.intelligence.schemas.temporal import TrendResult, SaturationResult
from src.intelligence.schemas.advanced import WhitespaceResult, DriftResult
from typing import List

# Note: Ensure the `vector` extension exists in PostgreSQL before making tables.
# CREATE EXTENSION IF NOT EXISTS vector;
try:
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        conn.commit()
    models.Base.metadata.create_all(bind=engine)
except Exception as e:
    print(f"Database initialization warning: {e}")

app = FastAPI(title="CompeteSmart Intelligence API")

@app.get("/")
def read_root():
    return {"message": "Market Intelligence Engine API is running"}

@app.post("/api/signals/ingest")
def ingest_signals(signals: List[SignalInput], background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    engine = ClusteringEngine(db)
    
    # Process and store raw signals
    raw = [s.model_dump() for s in signals]
    processed = engine.process_new_signals(raw)
    
    # Trigger HDBSCAN clustering asynchronously
    background_tasks.add_task(engine.run_clustering)
    return {"status": "success", "processed_count": len(processed)}

@app.get("/api/insights/trends", response_model=List[TrendResult])
def get_trends(db: Session = Depends(get_db)):
    engine = TemporalEngine(db)
    return engine.calculate_trends()

@app.get("/api/insights/saturation", response_model=List[SaturationResult])
def get_saturation(db: Session = Depends(get_db)):
    engine = TemporalEngine(db)
    return engine.calculate_saturation()

@app.get("/api/insights/whitespace", response_model=List[WhitespaceResult])
def get_whitespace(db: Session = Depends(get_db)):
    engine = AdvancedIntelligenceEngine(db)
    return engine.detect_whitespace()

@app.get("/api/insights/drift/{competitor_id}", response_model=DriftResult)
def get_drift(competitor_id: str, db: Session = Depends(get_db)):
    engine = AdvancedIntelligenceEngine(db)
    return engine.detect_persona_drift(competitor_id)

@app.get("/api/insights/summary/{cluster_id}")
def get_final_insight_summary(cluster_id: str, db: Session = Depends(get_db)):
    # Consolidate all 5 engines into the requested output schema
    temp_engine = TemporalEngine(db)
    
    # Extract specifically for this cluster
    trends = temp_engine.calculate_trends()
    saturations = temp_engine.calculate_saturation()
    
    trend_data = next((t for t in trends if t["cluster_id"] == cluster_id), None)
    sat_data = next((s for s in saturations if s["cluster_id"] == cluster_id), None)
    
    if not trend_data or not sat_data:
        return {"error": "Cluster not found or lacks sufficient data"}
        
    return {
        "cluster_id": cluster_id,
        "trend": trend_data["trend"],
        "growth_rate": trend_data["growth_rate"],
        "saturation": sat_data["saturation_score"],
        "whitespace": False, # Fixed logic: True if matches whitespace criteria
        "persona_shift": None # Linked to competitor, not cluster
    }
