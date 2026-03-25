from fastapi import FastAPI, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import text
from src.database import get_db, engine
from src import models
from src.intelligence.clustering import ClusteringEngine
from src.intelligence.temporal import TemporalEngine
from src.intelligence.advanced import AdvancedIntelligenceEngine
from src.intelligence.schemas import SignalInput, TrendResult, SaturationResult, WhitespaceResult, DriftResult
from src.auth import get_current_user
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

@app.post("/api/intelligence/run-pipeline")
def run_pipeline(background_tasks: BackgroundTasks, db: Session = Depends(get_db), user_id: str = Depends(get_current_user)):
    """
    Triggers the Intelligence loop:
    1. Scans DB for raw teammate signals and auto-embeds them (sync).
    2. Runs HDBSCAN semantic grouping algorithm.
    """
    engine = ClusteringEngine(db)
    background_tasks.add_task(engine.run_clustering)
    return {"status": "success", "message": "Intelligence pipeline triggered asynchronously in background!"}

@app.get("/api/insights/trends", response_model=List[TrendResult])
def get_trends(db: Session = Depends(get_db), user_id: str = Depends(get_current_user)):
    engine = TemporalEngine(db)
    return engine.calculate_trends()

@app.get("/api/insights/saturation", response_model=List[SaturationResult])
def get_saturation(db: Session = Depends(get_db), user_id: str = Depends(get_current_user)):
    engine = TemporalEngine(db)
    return engine.calculate_saturation()

@app.get("/api/insights/whitespace", response_model=List[WhitespaceResult])
def get_whitespace(db: Session = Depends(get_db), user_id: str = Depends(get_current_user)):
    engine = AdvancedIntelligenceEngine(db)
    return engine.detect_whitespace()

@app.get("/api/insights/drift/{competitor_id}", response_model=DriftResult)
def get_drift(competitor_id: str, db: Session = Depends(get_db), user_id: str = Depends(get_current_user)):
    engine = AdvancedIntelligenceEngine(db)
    return engine.detect_persona_drift(competitor_id)

@app.get("/api/insights/summary/{cluster_id}")
def get_final_insight_summary(cluster_id: str, db: Session = Depends(get_db), user_id: str = Depends(get_current_user)):
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

# ==========================================
# Frontend Chart Endpoints
# ==========================================

@app.get("/api/charts/opportunity")
def get_chart_opportunity(db: Session = Depends(get_db)):
    """
    Chart 4: Opportunity / Whitespace (Quadrant Chart)
    X-axis -> competition (frequency)
    Y-axis -> growth rate
    """
    temp_engine = TemporalEngine(db)
    trends = temp_engine.calculate_trends()
    
    chart_data = []
    for t in trends:
        # We need a quadrant classification based on your rule
        growth = t["growth_rate"]
        comp = t["current_count"]
        
        # Simple quadrant logic (you can adjust thresholds)
        if growth > 0.3 and comp < 5:
            quadrant = "BEST opportunity"
        elif growth > 0.3 and comp >= 5:
            quadrant = "Crowded"
        elif growth <= 0.3 and comp < 5:
            quadrant = "Weak"
        else:
            quadrant = "Avoid"
            
        chart_data.append({
            "name": t.get("cluster_label", "Unknown Theme"),
            "competition": comp,
            "growth": round(growth * 100, 2), # percentage
            "quadrant": quadrant,
            "trend": t["trend"]
        })
    return chart_data

@app.get("/api/charts/competitor-scores")
def get_chart_competitor_scores(db: Session = Depends(get_db)):
    """
    Chart 5: Competitor Comparison (Grouped Bar Chart)
    X-axis -> competitors
    Y-axis -> score (frequency / strength)
    """
    competitors = db.query(models.Competitor).all()
    chart_data = []
    
    # Define keywords for the pillars
    pillars = {
        "pricing": ["pricing", "price", "cost", "affordable", "budget", "cheap", "expensive"],
        "quality": ["quality", "premium", "best", "expert", "professional", "excellent", "certified"],
        "ai": ["ai", "automation", "smart", "intelligent", "algorithm", "machine", "tech"],
        "convenience": ["convenience", "fast", "quick", "easy", "doorstep", "simple", "hassle"]
    }
    
    for comp in competitors:
        comp_scores = {
            "competitor": comp.name,
            "pricing": 0,
            "quality": 0,
            "ai": 0,
            "convenience": 0
        }
        
        # Get all signals for this competitor
        signals = db.query(models.Signal).filter(models.Signal.competitor_id == comp.id).all()
        
        for sig in signals:
            content_lower = str(sig.content).lower()
            category_lower = str(sig.category).lower() if sig.category else ""
            
            # Score each pillar if keywords match
            for pillar, keywords in pillars.items():
                if any(kw in content_lower or kw in category_lower for kw in keywords):
                    comp_scores[pillar] += 1
                    
        chart_data.append(comp_scores)
        
    return chart_data

@app.get("/api/charts/risk-saturation")
def get_chart_risk_saturation(db: Session = Depends(get_db)):
    """
    Chart 6: Risk / Saturation (Gauge / Simple Bar)
    Shows saturation score and competition density to explicitly flag "What NOT to do".
    """
    temp_engine = TemporalEngine(db)
    saturations = temp_engine.calculate_saturation()
    
    chart_data = []
    for s in saturations:
        score = s["saturation_score"]
        
        if score > 0.7:
            risk_level = "high"
            color = "red"
            insight = "Avoid entering this heavily saturated market segment."
        elif score > 0.4:
            risk_level = "medium"
            color = "yellow"
            insight = "Monitor closely. Differentiation is required."
        else:
            risk_level = "low"
            color = "green"
            insight = "Clear to build. Low market saturation."
            
        chart_data.append({
            "cluster_id": s["cluster_id"],
            "name": s["cluster_label"],
            "saturation_score": round(score * 100, 2), # percentage
            "competition_density": s["competitors_using"],
            "risk_level": risk_level,
            "color": color,
            "insight": insight
        })
        
    return chart_data
