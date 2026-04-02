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
import logging
import sys
import time
from src.execution_copilot import chat_with_experiment

SUMMARY_CACHE = {
    "data": None,
    "timestamp": 0
}
CACHE_TTL = 300  # 5 minutes
# Configure logging to see progress in Render dashboard
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("api")

app = FastAPI(title="CompeteSmart Intelligence API")

@app.on_event("startup")
def startup_db():
    logger.info("Initializing database...")
    try:
        with engine.connect() as conn:
            # Ensure the `vector` extension exists in PostgreSQL
            logger.info("Checking for pgvector extension...")
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
            conn.commit()
        logger.info("Creating tables if they don't exist...")
        models.Base.metadata.create_all(bind=engine)
        logger.info("Database initialization complete.")
    except Exception as e:
        logger.error(f"Database initialization warning: {e}")

# Allow the Next.js frontend to call this API
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "https://compete-smart.vercel.app"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
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

class UserSetupRequest(BaseModel):
    name: str
    email: str
    company_name: str
    website: Optional[str] = None
    competitors: List[str]

class UserProfileResponse(BaseModel):
    name: str
    email: str
    company_name: str
    website: Optional[str] = None

class SuggestionRequest(BaseModel):
    company_name: str
    industry: Optional[str] = None
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

@app.get("/api/summary-insights")
def get_summary_insights(db: Session = Depends(get_db)):
    """Dynamic Executive Summary Cards with Caching"""
    
    current_time = time.time()
    if SUMMARY_CACHE["data"] and (current_time - SUMMARY_CACHE["timestamp"] < CACHE_TTL):
        return SUMMARY_CACHE["data"]

    # 1. Fastest Growing Competitor
    growth_query = """
    WITH recent AS (
        SELECT c.name, COUNT(*) AS cnt
        FROM extracted_content ec
        JOIN snapshots s ON ec.snapshot_id = s.id
        JOIN competitors c ON s.competitor_id = c.id
        WHERE ec.created_at >= NOW() - INTERVAL '30 days'
        GROUP BY c.name
    ),
    previous AS (
        SELECT c.name, COUNT(*) AS cnt
        FROM extracted_content ec
        JOIN snapshots s ON ec.snapshot_id = s.id
        JOIN competitors c ON s.competitor_id = c.id
        WHERE ec.created_at BETWEEN NOW() - INTERVAL '60 days' AND NOW() - INTERVAL '30 days'
        GROUP BY c.name
    )
    SELECT r.name,
    (r.cnt - COALESCE(p.cnt, 0)) AS growth
    FROM recent r
    LEFT JOIN previous p ON r.name = p.name
    ORDER BY growth DESC
    LIMIT 1;
    """
    try:
        growth_res = db.execute(text(growth_query)).fetchone()
        fastest_growing = {"name": growth_res[0], "growth": growth_res[1]} if growth_res else {"name": "N/A", "growth": 0}
    except Exception as e:
        logger.error(f"Error fetching growth: {e}")
        fastest_growing = {"name": "N/A", "growth": 0}

    # 2. Most Saturated Category
    sat_query = """
    SELECT cl.label AS theme, COUNT(*) AS density
    FROM signals s
    JOIN clusters cl ON s.cluster_id = cl.id
    WHERE s.cluster_id IS NOT NULL
    GROUP BY cl.label
    ORDER BY density DESC
    LIMIT 1;
    """
    try:
        sat_res = db.execute(text(sat_query)).fetchone()
        saturation = {"theme": sat_res[0] if sat_res else "N/A", "level": "high"}
    except Exception:
        saturation = {"theme": "N/A", "level": "high"}

    # 3. Top Opportunity Category
    opp_query = """
    SELECT cl.label AS theme, COUNT(*) AS density
    FROM signals s
    JOIN clusters cl ON s.cluster_id = cl.id
    WHERE s.cluster_id IS NOT NULL
    GROUP BY cl.label
    ORDER BY density ASC
    LIMIT 1;
    """
    try:
        opp_res = db.execute(text(opp_query)).fetchone()
        opportunity = {"theme": opp_res[0] if opp_res else "N/A", "level": "low"}
    except Exception:
        opportunity = {"theme": "N/A", "level": "low"}

    # 4. Clusters Tracked
    clusters_query = """
    SELECT COUNT(*) AS total_clusters FROM clusters;
    """
    try:
        clusters_res = db.execute(text(clusters_query)).fetchone()
        clusters_count = clusters_res[0] if clusters_res else 0
    except Exception:
        clusters_count = 0

    result = {
        "fastest_growing": fastest_growing,
        "saturation": saturation,
        "opportunity": opportunity,
        "clusters": {"count": clusters_count}
    }
    
    SUMMARY_CACHE["data"] = result
    SUMMARY_CACHE["timestamp"] = current_time
    
    return result

@app.get("/api/competitor-analysis")
def get_competitor_analysis(competitor: str = "ALL", db: Session = Depends(get_db)):
    # WHERE Clause based on selection
    where_clause_ec = "WHERE c.name = :comp" if competitor != "ALL" else ""
    where_clause_sig = "WHERE c.name = :comp" if competitor != "ALL" else ""
    params = {"comp": competitor} if competitor != "ALL" else {}

    # Trend Over Time
    time_filter = "ec.created_at >= NOW() - INTERVAL '18 months'"
    trend_where = f"{where_clause_ec} AND {time_filter}" if where_clause_ec else f"WHERE {time_filter}"

    trend_query = f"""
    SELECT 
        c.name AS competitor,
        TO_CHAR(DATE_TRUNC('month', ec.created_at), 'YYYY-MM') AS month,
        COUNT(*) AS activity
    FROM extracted_content ec
    JOIN snapshots s ON ec.snapshot_id = s.id
    JOIN competitors c ON s.competitor_id = c.id
    {trend_where}
    GROUP BY c.name, DATE_TRUNC('month', ec.created_at)
    ORDER BY DATE_TRUNC('month', ec.created_at) ASC;
    """
    trend_res = db.execute(text(trend_query), params).fetchall()
    trends = [{"competitor": row[0], "month": row[1], "activity": float(row[2])} for row in trend_res]

    # Theme Distribution
    theme_query = f"""
    SELECT 
        c.name AS competitor,
        s.category,
        ROUND((COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (PARTITION BY c.name)), 2) AS percentage
    FROM signals s
    JOIN competitors c ON s.competitor_id = c.id
    {where_clause_sig}
    GROUP BY c.name, s.category;
    """
    theme_res = db.execute(text(theme_query), params).fetchall()
    themes = [{"competitor": row[0], "category": row[1] if row[1] else "General", "percentage": float(row[2])} for row in theme_res]

    # Positioning Map
    pos_query = f"""
    WITH counts AS (
        SELECT c.name, COUNT(*) AS total
        FROM extracted_content ec
        JOIN snapshots s ON ec.snapshot_id = s.id
        JOIN competitors c ON s.competitor_id = c.id
        {where_clause_ec}
        GROUP BY c.name
    ),
    max_val AS (
        SELECT MAX(total) AS max_total FROM counts
    )
    SELECT 
        c.name,
        ROUND((c.total * 10.0 / m.max_total), 2) AS activity_score
    FROM counts c, max_val m;
    """
    pos_res = db.execute(text(pos_query), params).fetchall()
    
    # Mocking price_index and trust_score for scatter plot
    mock_pos = {
        "Urban Company": {"price_index": 8.5, "trust_score": 9.0},
        "Housejoy": {"price_index": 6.0, "trust_score": 6.5},
        "Sulekha": {"price_index": 4.0, "trust_score": 5.0}
    }
    
    positioning = []
    for row in pos_res:
        comp_name = row[0]
        pos_data = mock_pos.get(comp_name, {"price_index": 5.0, "trust_score": 5.0})
        positioning.append({
            "competitor": comp_name,
            "activity_score": float(row[1]),
            "price_index": pos_data["price_index"],
            "trust_score": pos_data["trust_score"]
        })

    # Whitespace Map
    white_query = f"""
    WITH competitor_scores AS (
        SELECT
            c.name AS competitor,
            COUNT(ec.id) AS activity
        FROM extracted_content ec
        JOIN snapshots s ON ec.snapshot_id = s.id
        JOIN competitors c ON s.competitor_id = c.id
        {where_clause_ec}
        GROUP BY c.name
    ),
    normalized AS (
        SELECT
            competitor,
            activity * 100.0 / MAX(activity) OVER () AS x
        FROM competitor_scores
    )
    SELECT
        competitor,
        x,
        RANDOM() * 100 AS y
    FROM normalized;
    """
    white_res = db.execute(text(white_query), params).fetchall()
    
    whitespace = []
    for row in white_res:
         # Map quadrant zones via mock logic temporarily if derived
         x_val = float(row[1])
         y_val = float(row[2])
         if y_val > 50 and x_val < 50:
             quadrant = "BEST opportunity"
         elif y_val > 50 and x_val >= 50:
             quadrant = "Crowded"
         elif y_val <= 50 and x_val < 50:
             quadrant = "Weak"
         else:
             quadrant = "Avoid"

         whitespace.append({
             "competitor": row[0],
             "x": round(x_val, 2),
             "y": round(y_val, 2),
             "quadrant": quadrant
         })

    # Competitor Strength
    strength_query = f"""
    WITH base AS (
        SELECT
            c.name AS competitor,
            COUNT(ec.id) AS total_activity
        FROM extracted_content ec
        JOIN snapshots s ON ec.snapshot_id = s.id
        JOIN competitors c ON s.competitor_id = c.id
        {where_clause_ec}
        GROUP BY c.name
    ),
    max_val AS (
        SELECT MAX(total_activity) AS max_total FROM base
    )
    SELECT
        b.competitor,
        ROUND((b.total_activity * 10.0 / m.max_total), 2) AS activity_score
    FROM base b, max_val m;
    """
    strength_res = db.execute(text(strength_query), params).fetchall()
    
    mock_dims = {
        "Urban Company": {"price": 6, "quality": 9, "convenience": 8, "ai": 9},
        "Housejoy": {"price": 8, "quality": 6, "convenience": 7, "ai": 4},
        "Sulekha": {"price": 9, "quality": 5, "convenience": 6, "ai": 3}
    }
    
    strength = []
    for row in strength_res:
        comp_name = row[0]
        dims = mock_dims.get(comp_name, {"price": 5, "quality": 5, "convenience": 5, "ai": 5})
        strength.append({
            "competitor": comp_name,
            "pricing": dims["price"],
            "quality": dims["quality"],
            "convenience": dims["convenience"],
            "ai": dims["ai"],
            "activity_score": float(row[1])
        })

    return {
        "trend": trends,
        "themes": themes,
        "positioning": positioning,
        "whitespace": whitespace,
        "strength": strength
    }

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

# --- User Setup & Profile Endpoints ---

@app.post("/api/user/setup")
def setup_user_profile(request: UserSetupRequest, db: Session = Depends(get_db), user_id: str = Depends(get_current_user)):
    """
    Saves the user's profile and their designated competitors.
    """
    # 1. Save or Update Profile
    profile = db.query(models.UserProfile).filter(models.UserProfile.user_id == user_id).first()
    if profile:
        profile.name = request.name
        profile.email = request.email
        profile.company_name = request.company_name
        profile.website = request.website
    else:
        profile = models.UserProfile(
            user_id=user_id,
            name=request.name,
            email=request.email,
            company_name=request.company_name,
            website=request.website
        )
        db.add(profile)
    
    # 2. Save Competitors
    # Mapping: admin_test_user -> client_id 1
    client_id = 1 if user_id == "admin_test_user" else 0
    
    for comp_name in request.competitors:
        # Check if already exists for this client
        exists = db.query(models.Competitor).filter(
            models.Competitor.name == comp_name,
            models.Competitor.client_id == client_id
        ).first()
        
        if not exists:
            new_comp = models.Competitor(name=comp_name, domain="", client_id=client_id)
            db.add(new_comp)
    
    db.commit()
    return {"status": "success", "message": "Profile and competitors saved successfully!"}

@app.get("/api/user/profile", response_model=UserProfileResponse)
def get_user_profile(db: Session = Depends(get_db), user_id: str = Depends(get_current_user)):
    """Retrieves the current user's profile."""
    profile = db.query(models.UserProfile).filter(models.UserProfile.user_id == user_id).first()
    if not profile:
        # Return default if not found (or 404)
        return {"name": "", "email": "", "company_name": ""}
    return profile

@app.get("/api/competitors/suggestions")
def get_competitor_suggestions(company_name: str, industry: Optional[str] = None):
    """
    Uses Gemini to suggest competitors based on company name and industry.
    """
    try:
        import google.generativeai as genai
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            return ["Competitor A", "Competitor B", "Competitor C"] # Fallback
            
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        prompt = f"Suggest 5 direct competitors for a company named '{company_name}'"
        if industry:
            prompt += f" in the {industry} industry."
        prompt += " Provide ONLY the names of the competitors as a comma-separated list."
        
        response = model.generate_content(prompt)
        # Clean response and convert to list
        names = [n.strip() for n in response.text.split(",") if n.strip()]
        return names[:5]
    except Exception as e:
        logger.error(f"Error getting suggestions: {e}")
        return ["Competitor X", "Competitor Y", "Competitor Z"]


if __name__ == "__main__":
    import uvicorn
    # Render provides the port in the PORT environment variable
    port = int(os.environ.get("PORT", 8000))
    logger.info(f"Starting uvicorn on 0.0.0.0:{port}")
    # Bind to 0.0.0.0 so the service is accessible externally
    uvicorn.run("api:app", host="0.0.0.0", port=port, log_level="info")
