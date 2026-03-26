from fastapi import FastAPI, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text, func
from src.database import get_db, engine
from src import models
from src.intelligence.clustering import ClusteringEngine
from src.intelligence.temporal import TemporalEngine
from src.intelligence.advanced import AdvancedIntelligenceEngine
from src.intelligence.schemas import SignalInput, TrendResult, SaturationResult, WhitespaceResult, DriftResult
from src.auth import get_current_user
from typing import List, Dict, Optional
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import os
import json
from src.execution_copilot import chat_with_experiment

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

# Allow the Next.js frontend to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Copilot & Experiment Schemas ---
class CopilotChatRequest(BaseModel):
    experiment_text: str
    user_query: str
    chat_history: Optional[List[Dict[str, str]]] = []
    cluster_id: Optional[str] = None

class CopilotChatResponse(BaseModel):
    response: str
@app.get("/api/trends")
def get_competitor_trends(client_id: int, db: Session = Depends(get_db), user_id: str = Depends(get_current_user)):
    """
    Returns time-series trend data for competitor messaging clusters.
    Groups signals by month (YYYY-MM) and cluster_id.
    """
    # Join Signal -> Snapshot -> Competitor to filter by client_id
    # Join Signal -> Cluster to get the readable label
    results = (
        db.query(
            models.Cluster.label.label("cluster_name"),
            func.to_char(models.Snapshot.created_at, "YYYY-MM").label("month"),
            func.count(models.Signal.id).label("count")
        )
        .join(models.Snapshot, models.Signal.snapshot_id == models.Snapshot.id)
        .join(models.Competitor, models.Signal.competitor_id == models.Competitor.id)
        .join(models.Cluster, models.Signal.cluster_id == models.Cluster.id)
        .filter(models.Competitor.client_id == client_id)
        .filter(models.Signal.cluster_id.isnot(None))
        .group_by(models.Cluster.label, "month")
        .order_by(models.Cluster.label, "month")
        .all()
    )

    # Reformat into the requested JSON structure
    clusters_map: Dict[str, List[Dict]] = {}
    for r in results:
        if r.cluster_name not in clusters_map:
            clusters_map[r.cluster_name] = []
        clusters_map[r.cluster_name].append({
            "date": r.month,
            "value": r.count
        })

    formatted_clusters = [
        {"name": name, "data": data}
        for name, data in clusters_map.items()
    ]

    return {"clusters": formatted_clusters}

@app.get("/api/positioning")
def get_competitor_positioning(client_id: int, db: Session = Depends(get_db), user_id: str = Depends(get_current_user)):
    """
    Generates a competitor positioning map (2D space).
    X-axis: Affordable (0) -> Premium (1)
    Y-axis: Feature-driven (0) -> Outcome-driven (1)
    """
    # Regex patterns for dimensions
    affordable_p = "price|cost|cheap|affordable|discount|deal|pricing"
    premium_p = "premium|luxury|professional|high-end|quality|experience|expert"
    feature_p = "service|equipment|chemical|tool|features|options"
    outcome_p = "clean|done|result|safe|convenience|transformation|outcome"

    # Aggregate counts per competitor
    # We use cast(..., Float) to ensure floating point division
    stats = (
        db.query(
            models.Competitor.name,
            func.count(models.Signal.id).filter(models.Cluster.label.op("~*")(premium_p)).label("premium"),
            func.count(models.Signal.id).filter(models.Cluster.label.op("~*")(affordable_p)).label("affordable"),
            func.count(models.Signal.id).filter(models.Cluster.label.op("~*")(outcome_p)).label("outcome"),
            func.count(models.Signal.id).filter(models.Cluster.label.op("~*")(feature_p)).label("feature")
        )
        .join(models.Signal, models.Competitor.id == models.Signal.competitor_id)
        .join(models.Cluster, models.Signal.cluster_id == models.Cluster.id)
        .filter(models.Competitor.client_id == client_id)
        .group_by(models.Competitor.name)
        .all()
    )

    # Get dominant cluster per competitor
    # This is a bit more complex in a single query, so we'll do a separate one or just pick the top from another join
    dominant_clusters = (
        db.query(
            models.Competitor.name,
            models.Cluster.label.label("top_cluster")
        )
        .join(models.Signal, models.Competitor.id == models.Signal.competitor_id)
        .join(models.Cluster, models.Signal.cluster_id == models.Cluster.id)
        .filter(models.Competitor.client_id == client_id)
        .group_by(models.Competitor.name, models.Cluster.label)
        .order_by(models.Competitor.name, func.count(models.Cluster.id).desc())
        .distinct(models.Competitor.name) # Postgres distinct on name picks the first row per group based on order_by
        .all()
    )
    dom_map = {d.name: d.top_cluster for d in dominant_clusters}

    competitors_data = []
    for s in stats:
        # Calculate X score (Affordable vs Premium)
        total_x = s.premium + s.affordable
        x = s.premium / total_x if total_x > 0 else 0.5
        
        # Calculate Y score (Feature vs Outcome)
        total_y = s.outcome + s.feature
        y = s.outcome / total_y if total_y > 0 else 0.5

        competitors_data.append({
            "name": s.name,
            "x": round(float(x), 2),
            "y": round(float(y), 2),
            "dominant_cluster": dom_map.get(s.name, "General")
        })

    return {"competitors": competitors_data}

@app.get("/api/distribution")
def get_messaging_distribution(client_id: int, db: Session = Depends(get_db), user_id: str = Depends(get_current_user)):
    """
    Computes messaging distribution across clusters for a given client.
    Returns percentages of the top 5 clusters.
    """
    # 1. Get total signal count for the client's competitors (excluding NULL cluster_id)
    total_count = (
        db.query(func.count(models.Signal.id))
        .join(models.Competitor, models.Signal.competitor_id == models.Competitor.id)
        .filter(models.Competitor.client_id == client_id)
        .filter(models.Signal.cluster_id.isnot(None))
        .scalar()
    )

    if not total_count or total_count == 0:
        return {"clusters": []}

    # 2. Aggregate counts per cluster
    results = (
        db.query(
            models.Cluster.label.label("name"),
            func.count(models.Signal.id).label("count")
        )
        .join(models.Signal, models.Cluster.id == models.Signal.cluster_id)
        .join(models.Competitor, models.Signal.competitor_id == models.Competitor.id)
        .filter(models.Competitor.client_id == client_id)
        .group_by(models.Cluster.label)
        .order_by(func.count(models.Signal.id).desc())
        .limit(5)
        .all()
    )

    # 3. Calculate percentages
    clusters_data = [
        {
            "name": r.name,
            "percentage": round((r.count / total_count) * 100, 1)
        }
        for r in results
    ]

    return {"clusters": clusters_data}

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
def get_chart_opportunity(client_id: int, db: Session = Depends(get_db), user_id: str = Depends(get_current_user)):
    """
    Chart 4: Opportunity / Whitespace (Quadrant Chart)
    X-axis -> competition (frequency)
    Y-axis -> growth rate
    """
    temp_engine = TemporalEngine(db)
    trends = temp_engine.calculate_trends(client_id=client_id)
    
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
def get_chart_competitor_scores(client_id: int, db: Session = Depends(get_db), user_id: str = Depends(get_current_user)):
    """
    Chart 5: Competitor Comparison (Grouped Bar Chart)
    X-axis -> competitors
    Y-axis -> score (frequency / strength)
    """
    # Optimized SQL approach: Use the Cluster labels directly to count signals per pillar
    # We define regex patterns for each pillar
    patterns = {
        "pricing": "pricing|price|cost|affordable|budget|cheap|expensive",
        "quality": "quality|premium|best|expert|professional|excellent|certified",
        "ai": "ai|automation|smart|intelligent|algorithm|machine|tech",
        "convenience": "convenience|fast|quick|easy|doorstep|simple|hassle"
    }

    competitors = db.query(models.Competitor).filter(models.Competitor.client_id == client_id).all()
    chart_data = []

    for comp in competitors:
        comp_scores = {"competitor": comp.name}
        for pillar, p_regex in patterns.items():
            count = (
                db.query(func.count(models.Signal.id))
                .join(models.Cluster, models.Signal.cluster_id == models.Cluster.id)
                .filter(models.Signal.competitor_id == comp.id)
                .filter(models.Cluster.label.op("~*")(p_regex))
                .scalar() or 0
            )
            comp_scores[pillar] = count
        chart_data.append(comp_scores)
        
    return chart_data

@app.get("/api/charts/risk-saturation")
def get_chart_risk_saturation(client_id: int, db: Session = Depends(get_db), user_id: str = Depends(get_current_user)):
    """
    Chart 6: Risk / Saturation (Gauge / Simple Bar)
    Shows saturation score and competition density to explicitly flag "What NOT to do".
    """
    temp_engine = TemporalEngine(db)
    saturations = temp_engine.calculate_saturation(client_id=client_id)
    
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

# ==========================================
# Copilot & Decision Layer Output
# ==========================================

@app.get("/api/experiments")
def get_suggested_experiments():
    """Returns the latest experiment recommendations from the decision layer."""
    output_path = "decision_layer_output.json"
    if not os.path.exists(output_path):
        return []
    
    try:
        with open(output_path, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error reading decision output: {e}")
        return []

@app.post("/api/copilot/chat", response_model=CopilotChatResponse)
def copilot_chat(request: CopilotChatRequest):
    """Answers user queries regarding a chosen experiment using AI RAG."""
    try:
        response_text = chat_with_experiment(
            experiment_text=request.experiment_text,
            user_query=request.user_query,
            chat_history=request.chat_history,
            cluster_id=request.cluster_id
        )
        return CopilotChatResponse(response=response_text)
    except Exception as e:
        return CopilotChatResponse(response=f"Copilot error: {str(e)}")
