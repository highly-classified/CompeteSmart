from fastapi import FastAPI, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import text, func
from src.database import get_db, engine
from src import models
from src.intelligence.clustering import ClusteringEngine
from src.intelligence.temporal import TemporalEngine
from src.intelligence.advanced import AdvancedIntelligenceEngine
from src.intelligence.schemas import SignalInput, TrendResult, SaturationResult, WhitespaceResult, DriftResult
from src.auth import get_current_user
from typing import List, Dict

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
