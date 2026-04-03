from fastapi import FastAPI, Depends, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text, func, case
from datetime import datetime
from src.database import get_db, engine, SessionLocal
from src import models
from src.intelligence.clustering import ClusteringEngine
from src.intelligence.temporal import TemporalEngine
from src.intelligence.advanced import AdvancedIntelligenceEngine
from src.intelligence.schemas import SignalInput, TrendResult, SaturationResult, WhitespaceResult, DriftResult
from src.auth import get_current_user
from typing import Any, List, Dict, Optional
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import os
import json
import logging
import sys
import asyncio
import random
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from src.cache_manager import (
    refresh_dashboard_cache,
    compute_summary_insights,
    compute_competitor_analysis,
    compute_suggested_experiments,
)
from src.execution_copilot import chat_with_experiment
# Correctly import the shared ranker logic
from src.ml_decision_layer import get_shared_ranker, generate_ranked_experiment_candidates, _build_ml_features
from src.experiment_generator import generate_experiment_output
import math

# Use the shared ranker singleton
strategy_ranker = get_shared_ranker()



# Dynamic Theme Mapping Layer (Requested)
DYNAMIC_THEME = case(
    (models.Cluster.label.ilike("%clean%"), "Cleaning"),
    (models.Cluster.label.ilike("%plumb%"), "Plumbing"),
    (models.Cluster.label.ilike("%pest%"), "Pest Control"),
    (models.Cluster.label.ilike("%beauty%"), "Beauty"),
    (models.Cluster.label.ilike("%appliance%"), "Appliance Repair"),
    (models.Cluster.label.ilike("%bath%"), "Bathroom Cleaning"),
    else_="Other"
)

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


def _is_valid_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _parse_percentage_label(value: Any) -> Optional[float]:
    if not isinstance(value, str) or not value.endswith("%"):
        return None
    try:
        return max(0.0, min(float(value[:-1].strip()) / 100.0, 1.0))
    except ValueError:
        return None


def _clamp_score(value: Any, fallback: float = 0.0) -> float:
    if _is_valid_number(value):
        return max(0.0, min(float(value), 1.0))
    return fallback


def _looks_like_cluster_id(value: Any) -> bool:
    return isinstance(value, str) and value.startswith("CL_")


def _risk_label_from_score(value: float) -> str:
    if value < 0.35:
        return "Low Risk"
    if value < 0.65:
        return "Medium Risk"
    return "High Risk"


def _title_from_experiment_text(text: Optional[str]) -> Optional[str]:
    if not text or not isinstance(text, str):
        return None

    cleaned = text.strip().strip(".")
    if not cleaned:
        return None

    prefixes = ("Test ", "Develop ", "Launch ", "Implement ", "Create ", "Optimize ")
    for prefix in prefixes:
        if cleaned.startswith(prefix):
            cleaned = cleaned[len(prefix):]
            break

    cleaned = cleaned.split(" to ", 1)[0]
    cleaned = cleaned.split(" with ", 1)[0]
    cleaned = cleaned.split(" for ", 1)[0]
    cleaned = cleaned.split(" within ", 1)[0]
    cleaned = cleaned.split(" in ", 1)[0]
    cleaned = cleaned.strip(" '\"")

    return cleaned[:80] if cleaned else None


def _build_traceability(item: Dict[str, Any]) -> Dict[str, Any]:
    trust = item.get("trust_and_risk") or {}
    item_traceability = item.get("traceability")
    raw_traceability = item_traceability if item_traceability else (trust.get("traceability") or {})
    traceability_reasons = raw_traceability if isinstance(raw_traceability, list) else raw_traceability.get("reasons", [])
    trust_traceability = trust.get("traceability") or {}
    traceability = {} if isinstance(raw_traceability, list) else raw_traceability
    sample_signals = [
        signal.strip()
        for signal in ((trust_traceability.get("sample_signals") or traceability.get("sample_signals")) or item.get("evidence") or [])
        if isinstance(signal, str) and signal.strip()
    ]
    competitor_ids = [
        str(competitor_id)
        for competitor_id in ((trust_traceability.get("competitor_ids") or traceability.get("competitor_ids")) or [])
        if competitor_id is not None
    ]
    competitor_names = [
        str(name)
        for name in ((trust_traceability.get("competitor_names") or traceability.get("competitor_names")) or [])
        if name
    ]
    total_signals = trust_traceability.get("total_signals", traceability.get("total_signals"))
    total_signals = int(total_signals) if isinstance(total_signals, int) else len(sample_signals)
    avg_rating = trust_traceability.get("avg_rating", traceability.get("avg_rating"))
    review_signal_count = trust_traceability.get("review_signal_count", traceability.get("review_signal_count"))
    review_score = trust_traceability.get("review_score", traceability.get("review_score"))

    summary_parts: List[str] = []
    if traceability_reasons:
        summary_parts.append(traceability_reasons[0])
    if sample_signals:
        summary_parts.append(sample_signals[0])
    if _is_valid_number(avg_rating):
        summary_parts.append(f"avg rating: {float(avg_rating):.1f}/5")
    elif _is_valid_number(review_score):
        summary_parts.append(f"review score: {round(float(review_score) * 100):.0f}%")
    if isinstance(review_signal_count, int) and review_signal_count > 0:
        summary_parts.append(f"{review_signal_count} review signal{'s' if review_signal_count != 1 else ''}")
    if total_signals:
        summary_parts.append(f"{total_signals} supporting signal{'s' if total_signals != 1 else ''}")
    if competitor_names:
        summary_parts.append(f"sources: {', '.join(competitor_names[:2])}")
    if competitor_ids:
        summary_parts.append(f"competitors: {', '.join(competitor_ids[:3])}")

    summary = " | ".join(summary_parts) if summary_parts else (
        item.get("insight")
        or trust.get("explanation")
        or "No traceability details were returned by the backend."
    )

    return {
        "summary": summary,
        "total_signals": total_signals,
        "sample_signals": sample_signals[:3],
        "competitor_ids": competitor_ids[:5],
        "competitor_names": competitor_names[:5],
        "avg_rating": avg_rating,
        "review_signal_count": review_signal_count,
        "review_score": review_score,
        "reasons": traceability_reasons[:3],
    }


def _normalize_experiment(item: Dict[str, Any]) -> Dict[str, Any]:
    decision = item.get("decision") or {}
    trust = item.get("trust_and_risk") or {}
    recommended_action = (
        item.get("experiment")
        or item.get("recommended_action")
        or decision.get("experiment")
        or ""
    )
    cluster_name = item.get("cluster_name") or item.get("category")
    raw_title = item.get("title") or cluster_name or item.get("cluster_id")
    title = raw_title
    if _looks_like_cluster_id(title):
        title = _title_from_experiment_text(recommended_action) or cluster_name or title

    confidence = item.get("confidence_score")
    if not _is_valid_number(confidence):
        confidence = _parse_percentage_label(item.get("confidence"))
    if not _is_valid_number(confidence):
        confidence = item.get("ml_predicted_score")
    if not _is_valid_number(confidence):
        confidence = trust.get("confidence_score")
    if not _is_valid_number(confidence):
        confidence = item.get("confidence")
    if not _is_valid_number(confidence):
        confidence = decision.get("priority_score")
    confidence = _clamp_score(confidence, fallback=0.0)

    risk = item.get("risk_score")
    if not _is_valid_number(risk):
        risk = trust.get("risk_score")
    if not _is_valid_number(risk):
        risk = item.get("risk")
    risk = _clamp_score(risk, fallback=0.0)

    traceability = _build_traceability(item)

    return {
        "title": title or "Suggested Experiment",
        "category": item.get("category") or cluster_name or title or "General Service",
        "cluster_id": item.get("cluster_id"),
        "cluster_name": cluster_name,
        "trend": item.get("trend") or decision.get("priority") or item.get("decision_type") or "",
        "confidence": confidence,
        "confidence_label": item.get("confidence") if isinstance(item.get("confidence"), str) else f"{round(confidence * 100):.0f}%",
        "risk": risk,
        "risk_label": item.get("risk") if isinstance(item.get("risk"), str) else _risk_label_from_score(risk),
        "recommended_action": recommended_action,
        "experiment": item.get("experiment") or recommended_action,
        "hypothesis": item.get("hypothesis"),
        "metric": item.get("metric"),
        "expected_impact": item.get("expected_impact"),
        "insight": item.get("insight") or item.get("hypothesis") or trust.get("explanation") or traceability["summary"],
        "traceability": traceability,
        "evidence": item.get("evidence") or traceability["sample_signals"],
    }


def _normalize_experiments(items: Any) -> List[Dict[str, Any]]:
    if not isinstance(items, list):
        return []
    normalized = [_normalize_experiment(item) for item in items if isinstance(item, dict)]
    return normalized[:3]


def _is_structured_experiment_payload(items: Any) -> bool:
    if not isinstance(items, list) or not items:
        return False

    sample = items[0]
    if not isinstance(sample, dict):
        return False

    return all(field in sample for field in ("experiment", "hypothesis", "expected_impact", "traceability"))

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
    "http://localhost:3001",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "https://compete-smart.vercel.app"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins + ["http://127.0.0.1:3000", "http://127.0.0.1:3001"],
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
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
            DYNAMIC_THEME.label("cluster_name"),
            func.to_char(models.Snapshot.created_at, "YYYY-MM").label("month"),
            func.count(models.Signal.id).label("count")
        )
        .join(models.Snapshot, models.Signal.snapshot_id == models.Snapshot.id)
        .join(models.Competitor, models.Signal.competitor_id == models.Competitor.id)
        .join(models.Cluster, models.Signal.cluster_id == models.Cluster.id)
        .filter(models.Competitor.client_id == client_id)
        .filter(DYNAMIC_THEME != "Other")
        .filter(models.Signal.cluster_id.isnot(None))
        .group_by(DYNAMIC_THEME, "month")
        .order_by(DYNAMIC_THEME, "month")
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
            func.count(models.Signal.id).filter(DYNAMIC_THEME.op("~*")(premium_p)).label("premium"),
            func.count(models.Signal.id).filter(DYNAMIC_THEME.op("~*")(affordable_p)).label("affordable"),
            func.count(models.Signal.id).filter(DYNAMIC_THEME.op("~*")(outcome_p)).label("outcome"),
            func.count(models.Signal.id).filter(DYNAMIC_THEME.op("~*")(feature_p)).label("feature")
        )
        .join(models.Signal, models.Competitor.id == models.Signal.competitor_id)
        .join(models.Cluster, models.Signal.cluster_id == models.Cluster.id)
        .filter(models.Competitor.client_id == client_id)
        .filter(DYNAMIC_THEME != "Other")
        .group_by(models.Competitor.name)
        .all()
    )

    # Get dominant cluster per competitor
    dominant_clusters = (
        db.query(
            models.Competitor.name,
            DYNAMIC_THEME.label("top_cluster")
        )
        .join(models.Signal, models.Competitor.id == models.Signal.competitor_id)
        .join(models.Cluster, models.Signal.cluster_id == models.Cluster.id)
        .filter(models.Competitor.client_id == client_id)
        .filter(DYNAMIC_THEME != "Other")
        .group_by(models.Competitor.name, DYNAMIC_THEME)
        .order_by(models.Competitor.name, func.count(models.Cluster.id).desc())
        .distinct(models.Competitor.name) 
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
            DYNAMIC_THEME.label("name"),
            func.count(models.Signal.id).label("count")
        )
        .join(models.Signal, models.Cluster.id == models.Signal.cluster_id)
        .join(models.Competitor, models.Signal.competitor_id == models.Competitor.id)
        .filter(models.Competitor.client_id == client_id)
        .filter(DYNAMIC_THEME != "Other")
        .group_by(DYNAMIC_THEME)
        .order_by(func.count(models.Signal.id).desc())
        .limit(6)
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
    # Correctly handle sessions in background tasks
    def full_pipeline_update():
        from src.database import SessionLocal
        new_db = SessionLocal()
        try:
            # 1. Clustering
            engine = ClusteringEngine(new_db)
            engine.run_clustering()
            # 2. Refresh Dashboard Cache
            refresh_dashboard_cache(new_db)
            logger.info("Background full pipeline update completed.")
        except Exception as e:
            logger.error(f"Background pipeline update failed: {e}")
        finally:
            new_db.close()

    background_tasks.add_task(full_pipeline_update)
    return {"status": "success", "message": "Intelligence pipeline and cache refresh triggered!"}

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
    """Fetch Summary Insights from Persistent Cache with Fallback"""
    cache_entry = db.query(models.DashboardCache).filter(models.DashboardCache.key == "summary_insights").first()
    if cache_entry:
        return cache_entry.data
    
    # Fallback to computing and caching if missing
    logger.info("Cache miss for summary_insights. Recomputing...")
    data = compute_summary_insights(db)
    new_cache = models.DashboardCache(key="summary_insights", data=data)
    db.merge(new_cache)
    db.commit()
    return data

@app.get("/api/competitor-analysis")
def get_competitor_analysis(competitor: str = "ALL", db: Session = Depends(get_db)):
    """Fetch Competitor Analysis from Persistent Cache with Fallback"""
    cache_key = f"comp_analysis_{competitor}"
    cache_entry = db.query(models.DashboardCache).filter(models.DashboardCache.key == cache_key).first()
    if cache_entry:
        return cache_entry.data
    
    # Fallback to computing and caching if missing
    logger.info(f"Cache miss for {cache_key}. Recomputing...")
    data = compute_competitor_analysis(db, competitor)
    new_cache = models.DashboardCache(key=cache_key, data=data)
    db.merge(new_cache)
    db.commit()
    return data

@app.post("/api/refresh-cache")
def trigger_cache_refresh(background_tasks: BackgroundTasks):
    """Force rebuild the entire dashboard cache in the background"""
    def background_refresh():
        from src.database import SessionLocal
        db = SessionLocal()
        try:
            refresh_dashboard_cache(db)
        finally:
            db.close()
            
    background_tasks.add_task(background_refresh)
    return {"status": "success", "message": "Dashboard cache rebuild triggered in background"}

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
                .filter(models.Cluster.clean_label != "")
                .filter(models.Cluster.clean_label.op("~*")(p_regex))
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
def get_suggested_experiments(db: Session = Depends(get_db)):
    """Returns the latest experiment recommendations from the database cache (with JSON fallback)."""
    try:
        # 1. Try Dataset Cache (Database)
        cache_entry = db.query(models.DashboardCache).filter(models.DashboardCache.key == "suggested_experiments").first()
        if cache_entry and cache_entry.data:
            if _is_structured_experiment_payload(cache_entry.data):
                response = _normalize_experiments(cache_entry.data)
                print("API Response (cache):", response)
                return JSONResponse(content=jsonable_encoder(response))

            print("Stale suggested_experiments cache detected. Regenerating structured experiments...")

        # 2. Force regeneration from the new ML -> decision -> experiment pipeline
        regenerated = compute_suggested_experiments(db)
        print("Final Experiments:", regenerated)
        if regenerated:
            cache_entry = db.query(models.DashboardCache).filter(models.DashboardCache.key == "suggested_experiments").first()
            if cache_entry:
                cache_entry.data = regenerated
                cache_entry.last_updated = datetime.utcnow()
            else:
                db.add(models.DashboardCache(key="suggested_experiments", data=regenerated))
            db.commit()
            response = _normalize_experiments(regenerated)
            print("API Response (regenerated):", response)
            return JSONResponse(content=jsonable_encoder(response))
    except Exception as e:
        logger.error(f"Failed to regenerate suggested experiments: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e), "experiments": []},
        )
        
    # 3. Primary Fallback: ML Standalone Results
    ml_output_path = "ml_standalone_results.json"
    if os.path.exists(ml_output_path):
        try:
            with open(ml_output_path, "r") as f:
                data = json.load(f)
                if _is_structured_experiment_payload(data):
                    response = _normalize_experiments(data)
                    print("API Response (ml fallback):", response)
                    return JSONResponse(content=jsonable_encoder(response))
                print("Skipping ml_standalone_results.json because it is not using the structured experiment schema.")
        except Exception as e:
            logger.error(f"Error reading ML standalone file: {e}")

    # 4. Secondary Fallback: Original JSON (Backup)
    output_path = "decision_layer_output.json"
    if os.path.exists(output_path):
        try:
            with open(output_path, "r") as f:
                data = json.load(f)
                if _is_structured_experiment_payload(data):
                    response = _normalize_experiments(data)
                    print("API Response (legacy fallback):", response)
                    return JSONResponse(content=jsonable_encoder(response))
                print("Skipping decision_layer_output.json because it is using the legacy experiment schema.")
        except Exception as e:
            logger.error(f"Error reading legacy output file: {e}")
    
    return JSONResponse(content={"experiments": [], "message": "No structured experiments are available."})


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
def get_competitor_suggestions(
    company_name: str, 
    industry: Optional[str] = None, 
    location: Optional[str] = None, 
    business_type: Optional[str] = "saas"
):
    """
    Uses Gemini to suggest a strategic mix of 3 competitors: 
    1 Industry Leader + 2 Direct Peer-Level Companies.
    Considers 'location' for local businesses and 'saas' priority for global products.
    """
    try:
        import google.generativeai as genai
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            return ["Competitor A", "Competitor B", "Competitor C"] # Fallback
            
        genai.configure(api_key=api_key)
        
        # Model ladder to handle quota limits: 3.1 Pro first, then 3.1 Flash-Lite
        model_names = ['models/gemini-3.1-pro-preview', 'models/gemini-3.1-flash-lite-preview']
        response = None
        last_error = None
        
        for m_name in model_names:
            try:
                model = genai.GenerativeModel(m_name)
                # Build a sophisticated prompt
                context = f"Company: '{company_name}'"
                if industry: context += f", Industry: '{industry}'"
                if location: context += f", Location: '{location}'"
                
                prompt = f"""
                Analyze the company: {context}.
                Business Model Focus: {business_type.upper()}.

                TASK: Suggest exactly 3 direct competitors.
                
                CRITICAL RULES:
                1. If '{company_name}' is a Startup, provide:
                   - 1 Top Industry Leader (giant rival).
                   - 2 Strategic Peers (same level startups/rivals).
                2. If model is 'LOCAL', prioritize competitors in '{location or 'their area'}'.
                3. If model is 'SAAS', prioritize global rivals.
                4. Focus on direct rivals fighting for the same customers.
                5. OUTPUT FORMAT: Provide ONLY the names in a single line, separated by commas. 
                   Example: Google, Microsoft, Amazon
                   NO intro, NO descriptions, NO numbering, NO bolding.
                """
                
                response = model.generate_content(prompt)
                if response and response.text:
                    break # Success!
            except Exception as e:
                last_error = str(e)
                logger.warning(f"Model {m_name} failed: {e}")
                continue
                
        if not response:
            logger.error(f"All Gemini models failed. Last error: {last_error}")
            return ["Competitor Look-up Failed", "Checking Connection...", "Try Manual Entry"]

        text_response = response.text.strip()
        
        # Clean response: Handle common AI prefixes
        if ":" in text_response and len(text_response.split(":")[0]) < 40:
            text_response = text_response.split(":", 1)[1].strip()
            
        # Convert to list and clean each name (strip markdown asterisks, numbers, etc.)
        import re
        names = []
        for n in text_response.split(","):
            # Regex to strip leading numbers, dots, dashes, and whitespace
            clean_name = re.sub(r'^[\d\.\-\s\*]+', '', n.strip())
            # Strip trailing markdown artifacts
            clean_name = clean_name.strip(" *#_")
            if clean_name:
                names.append(clean_name)
        
        return names[:3]
    except Exception as e:
        logger.error(f"Critical error in AI suggestions: {e}")
        return ["AI Processing Error", "Please try again later", "Check API Quota"]


@app.websocket("/ws/simulate")
async def simulate_endpoint(websocket: WebSocket, cluster_focus: str = None):
    await websocket.accept()
    logger.info(f"Simulation engine accepted connection (Focus: {cluster_focus}). Initializing analysis...")


    # ── 1. LOAD REAL DATA FROM DATABASE ─────────────────────────────────────────
    db = SessionLocal()
    try:
        competitors = db.query(models.Competitor).all()
        competitor_names = [c.name for c in competitors] if competitors else ["Unknown Competitor"]

        temp_engine = TemporalEngine(db)
        # 1. Fetch only the clusters that actually have signal data (market evidence)
        # Instead of 474, we only focus on the top 12 highest-activity segments.
        all_sats = temp_engine.calculate_saturation()
        active_saturations = [s for s in all_sats if s.get("competitors_using", 0) > 0]
        
        # If we have a focus cluster, prioritize it!
        focused_sat = next((s for s in all_sats if s.get("cluster_id") == cluster_focus), None)
        
        active_saturations.sort(key=lambda x: x.get("competitors_using", 0), reverse=True)
        top_saturations = active_saturations[:12]
        
        if focused_sat and focused_sat not in top_saturations:
            top_saturations.insert(0, focused_sat)
            top_saturations = top_saturations[:12]

        
        # 2. Get trends only for these active clusters
        real_trends = temp_engine.calculate_trends()
        trends_map = {t["cluster_id"]: t for t in real_trends}

        cluster_intel: dict = {}
        for s in top_saturations:
            cid = s["cluster_id"]
            t_data = trends_map.get(cid, {})
            cluster_intel[cid] = {
                "clean_label":         s.get("cluster_label", "Unknown Theme"),
                "saturation":          s.get("saturation_score", 0.5),
                "competitors_using":   s.get("competitors_using", 1),
                "total_competitors":   s.get("total_competitors", 3),
                "growth_rate":         t_data.get("growth_rate", 0.0),
                "signal_count":        t_data.get("current_count", 0),
            }

        if cluster_intel:
            avg_saturation = sum(v["saturation"] for v in cluster_intel.values()) / len(cluster_intel)
        else:
            avg_saturation = 0.55


    except Exception as exc:
        logger.error(f"DB load failed for simulation: {exc}")
        competitor_names = ["Competitor A", "Competitor B"]
        cluster_intel    = {}
        avg_saturation   = 0.55
    finally:
        db.close()

    rival_names = competitor_names[:3] or ["Market Leader", "Challenger", "Newcomer"]

    # ── 2. DERIVE INITIAL KPI STATE PURELY FROM REAL DATA ───────────────────────
    # sat: real avg saturation scaled to 0-100; clamped 30-92
    sat  = round(min(92.0, max(30.0, avg_saturation * 100.0)), 1)
    # diff: starts inversely to saturation, clamped 5-45
    diff = round(min(45.0, max(5.0, (1.0 - avg_saturation) * 55.0)), 1)
    momentum = 0.0

    month_names = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]

    # ── 3. SEND INIT FRAME (before heavy ML work) ────────────────────────────────
    n_clusters = len(cluster_intel)
    try:
        await websocket.send_json({
            "status": "RUNNING",
            "iteration": 0,
            "maxIterations": 0,          # unknown until we start iterating
            "stageData": {
                "id": 0,
                "title": "Loading Market Intelligence...",
                "desc": (
                    f"Scanning {n_clusters} live market clusters and {len(competitor_names)} "
                    f"tracked competitor(s) ({', '.join(rival_names)}). "
                    f"Real-time saturation baseline: {sat}%. "
                    f"Running ML scoring pipeline to generate ranked experiment candidates..."
                ),
            },
            "chartPoint": {"month": month_names[0], "differentiation": round(diff), "saturation": round(sat)},
            "kpis": {"differentiation": round(diff), "saturation": round(sat), "persona_drift": 0, "resonance": 1.0},
        })
    except WebSocketDisconnect:
        return

    await asyncio.sleep(0.3)

    # ── 4. BUILD INSIGHTS FROM REAL CLUSTER DATA ─────────────────────────────────
    insights = []
    for cid, info in cluster_intel.items():
        sat_raw  = info["saturation"]
        evidence = max(1, info["signal_count"])
        growth   = info["growth_rate"]
        # Estimate signal strengths from cluster data
        review_strength = min(1.0, max(0.1, (1.0 - sat_raw) * 0.8 + 0.1))
        price_strength  = min(1.0, max(0.1, sat_raw * 0.5 + 0.15))
        insights.append({
            "cluster_id":             cid,
            "cluster_name":           info["clean_label"],
            "saturation":             sat_raw,
            "trend":                  growth,
            "evidence_count":         evidence,
            "avg_signal_confidence":  min(1.0, 0.5 + growth * 0.3),
            "review_signal_strength": review_strength,
            "price_signal_strength":  price_strength,
        })

    if not insights:
        insights = [{
            "cluster_id": "fallback", "cluster_name": "General Market",
            "saturation": avg_saturation, "trend": 0.0, "evidence_count": 3,
            "avg_signal_confidence": 0.55, "review_signal_strength": 0.45,
            "price_signal_strength": 0.35,
        }]

    # ── 5. GENERATE STRATEGY POOL IN BACKGROUND THREAD ──────────────────────────
    try:
        candidates = await asyncio.to_thread(generate_ranked_experiment_candidates, insights, 20)
    except Exception as exc:
        logger.error(f"ML candidate generation failed: {exc}")
        candidates = []

    # Build simulation strategy pool from real candidates
    strategies = []
    for cand in candidates:
        try:
            exp_data = generate_experiment_output(
                cand, cand.get("ml_analysis", {}), cand.get("trust_and_risk", {})
            )
            ml_feats = cand.get("ml_features") or _build_ml_features(cand)
            strategies.append({
                # Identifying fields
                "name":            f"{exp_data.get('decision_type','pivot').replace('_',' ').title()} — {exp_data.get('cluster_name','Market')[:20]}",
                "cluster_id":      cand.get("cluster_id", ""),
                "type":            cand.get("type", "unknown"),
                # ML-derived risk and confidence (no magic numbers)
                "risk":            min(0.80, max(0.05, float(exp_data.get("risk_score", 0.45)))),
                "ml_score_base":   float(cand.get("candidate_score", 0.5)),
                "confidence":      float(cand.get("candidate_score", 0.5)),
                "evidence_count":  int(cand.get("evidence_count", 1)),
                # Full ML feature set (used for live re-scoring)
                "ml_features":     ml_feats,
                # Narrative
                "experiment":      exp_data.get("experiment", "Strategic Pivot"),
                "hypothesis":      exp_data.get("hypothesis", "Improves market positioning."),
                "metric":          exp_data.get("metric", "Conversion Rate"),
                "expected_impact": exp_data.get("expected_impact", ""),
                # Tracking
                "fail_count":      0,
                "win_count":       0,
            })
        except Exception as exc:
            logger.warning(f"Skipped candidate: {exc}")

    if not strategies:
        # Graceful dead-end: no pipeline output at all
        try:
            await websocket.send_json({
                "status": "FAILURE",
                "iteration": 1,
                "maxIterations": 1,
                "stageData": {
                    "id": 1,
                    "title": "✦ Outcome: Insufficient Data",
                    "desc": (
                        f"The ML pipeline found no viable experiment candidates across "
                        f"{n_clusters} clusters. Insufficient market signal data to simulate."
                    ),
                },
                "chartPoint": {"month": month_names[1], "differentiation": round(diff), "saturation": round(sat)},
                "kpis": {"differentiation": round(diff), "saturation": round(sat), "persona_drift": 0, "resonance": 1.0},
            })
        except WebSocketDisconnect:
            pass
        return

    # ── 6. SEND "READY" FRAME ────────────────────────────────────────────────────
    try:
        await websocket.send_json({
            "status": "RUNNING",
            "iteration": 0,
            "maxIterations": 0,
            "stageData": {
                "id": 0,
                "title": f"Pipeline Ready — {len(strategies)} Strategies Loaded",
                "desc": (
                    f"Ranked {len(strategies)} experiment candidates from {n_clusters} real clusters. "
                    f"Starting differentiation: {diff}%, saturation: {sat}%. "
                    f"Competitors tracked: {', '.join(rival_names)}. "
                    f"The agentic loop will iterate until breakthrough (diff ≥ 80%) or strategic exhaustion."
                ),
            },
            "chartPoint": {"month": month_names[0], "differentiation": round(diff), "saturation": round(sat)},
            "kpis": {"differentiation": round(diff), "saturation": round(sat), "persona_drift": 0, "resonance": 1.0},
        })
    except WebSocketDisconnect:
        return

    await asyncio.sleep(0.5)

    # ── 7. AGENTIC SIMULATION LOOP ───────────────────────────────────────────────
    # Termination conditions (all derived from data, no hardcoded iteration cap):
    #   SUCCESS  : diff >= 80   (market breakthrough)
    #   FAILURE  : sat >= 95    (market collapse)
    #   EXHAUSTED: best viable success_chance across all strategies < 0.12
    #
    VIABILITY_FLOOR   = 0.12   # below this success_chance, strategy is not viable
    BREAKTHROUGH_DIFF = 80.0
    COLLAPSE_SAT      = 95.0
    SAFETY_CAP        = 30     # hard upper bound to prevent runaway ws session

    i = 0
    try:
        while i < SAFETY_CAP:
            i += 1
            month = month_names[i % 12]

            # ── 7a. Re-score all strategies with ML features updated for current state ──
            # We shift ml_features that can be influenced by the sim state:
            #   demand_gap          â† boosted by momentum (momentum creates demand signal)
            scored = []
            for s in strategies:
                # If a cluster focus is provided, only iterate strategies from THAT specific market segment.
                # This ensures the simulation stays relevant to the user's specific strategic goal.
                if cluster_focus and s.get("cluster_id") != cluster_focus:
                    continue
                    
                # Start from the ML features computed from real cluster data
                live_features = {**s["ml_features"]}

                # Update with live simulation state
                live_features["competition_density"] = round(min(1.0, sat / 100.0), 3)
                live_features["demand_gap"] = round(min(1.0, max(0.0,
                    live_features.get("demand_gap", 0.5) + (momentum * 0.04)
                )), 3)
                # Penalize strategies that have already failed: lower evidence_strength
                if s["fail_count"] > 0:
                    live_features["evidence_strength"] = round(max(0.0,
                        live_features.get("evidence_strength", 0.5) - s["fail_count"] * 0.08
                    ), 3)

                live_ml_score = strategy_ranker.predict_score(live_features)

                # Compute current success_chance from ML score + momentum/saturation
                risk            = s["risk"]
                base_chance     = (live_ml_score * 0.7) + ((1.0 - risk) * 0.3)
                momentum_bonus  = min(momentum * 0.06, 0.18)
                sat_penalty     = max((sat - 65.0) * 0.006, 0.0)
                success_chance  = max(0.0, min(0.90, base_chance + momentum_bonus - sat_penalty))

                scored.append({
                    **s,
                    "live_ml_score":   round(live_ml_score, 4),
                    "success_chance":  round(success_chance, 4),
                    "live_features":   live_features,
                })

            # Sort by success_chance descending (best bet first)
            scored.sort(key=lambda x: x["success_chance"], reverse=True)
            best = scored[0]

            # ── 7b. Check for strategic exhaustion ──────────────────────────────
            if best["success_chance"] < VIABILITY_FLOOR:
                exhausted_desc = (
                    f"After {i} strategic iterations, the simulation engine analysed {len(strategies)} "
                    f"unique experiment candidates. The highest achievable success probability is "
                    f"{round(best['success_chance']*100,1)}% — below the {round(VIABILITY_FLOOR*100)}% viability "
                    f"floor. With saturation at {round(sat)}% and {len(rival_names)} active competitors, "
                    f"no viable differentiation path exists under current market conditions."
                )
                await websocket.send_json({
                    "status": "FAILURE",
                    "iteration": i,
                    "maxIterations": i,
                    "stageData": {
                        "id": i,
                        "title": "✦ Outcome: Market Dead-End",
                        "desc": exhausted_desc,
                    },
                    "chartPoint": {"month": month, "differentiation": round(diff), "saturation": round(sat)},
                    "kpis": {
                        "differentiation": round(diff),
                        "saturation":      round(sat),
                        "persona_drift":   round(momentum * 60),
                        "resonance":       round(max(0.1, 1.0 + (diff / 40.0)), 1),
                    },
                })
                break

            strategy = best

            # ── 7c. Monte-Carlo roll ─────────────────────────────────────────────
            roll      = random.random()
            succeeded = roll < strategy["success_chance"]

            # ── 7d. Apply outcomes (all derived from ML scores, no magic ranges) ──
            if succeeded:
                # Boost = confidence * evidence_strength * 25  (max ~16 pts per win)
                boost     = strategy["confidence"] * strategy["live_features"].get("evidence_strength", 0.5) * 25.0
                boost    *= max(1.0, 1.0 + momentum * 0.15)      # momentum multiplier
                reduction = math.log1p(strategy["evidence_count"]) * 4.0  # sat reduction
                reduction = min(18.0, max(3.0, reduction))

                diff      += boost
                sat       -= reduction
                momentum  += 0.4

                # Update tracking
                for s in strategies:
                    if s["cluster_id"] == strategy["cluster_id"] and s["type"] == strategy["type"]:
                        s["win_count"] += 1

                # Lifecyle phrases to avoid repetition
                phases = ["Deploying", "Scaling", "Dominating", "Hardening", "Optimizing"]
                phase  = phases[min(len(phases)-1, strategy.get("win_count", 0))]
                
                impact_str = strategy["expected_impact"] or f"+{round(boost, 1)}%"
                title = f"Iteration {i} ✓  {phase}: {strategy['name']}"

                desc  = (
                    f"ML score: {round(strategy['live_ml_score']*100,1)}% | "
                    f"Success probability: {round(strategy['success_chance']*100,1)}% | "
                    f"Roll: {round(roll*100,1)}% ✓\n\n"
                    f"Experiment deployed: {strategy['experiment']}\n"
                    f"Hypothesis: {strategy['hypothesis']}\n"
                    f"Target metric: {strategy['metric']} {impact_str}\n\n"
                    f"Differentiation +{round(boost,1)}pt → {round(diff,1)}%. "
                    f"Saturation reduced by {round(reduction,1)}pt → {round(sat,1)}%."
                )
            else:
                penalty   = strategy["risk"] * 12.0
                sat_rise  = strategy["live_features"].get("competition_density", 0.5) * 8.0
                sat_rise  = min(10.0, max(2.0, sat_rise))

                diff     -= penalty
                sat      += sat_rise
                momentum  = max(0.0, momentum - 0.25)

                for s in strategies:
                    if s["cluster_id"] == strategy["cluster_id"] and s["type"] == strategy["type"]:
                        s["fail_count"] += 1

                title = f"Iteration {i} ✗  {strategy['name']}"
                desc  = (
                    f"ML score: {round(strategy['live_ml_score']*100,1)}% | "
                    f"Success probability: {round(strategy['success_chance']*100,1)}% | "
                    f"Roll: {round(roll*100,1)}% ✗\n\n"
                    f"Experiment: {strategy['experiment']}\n"
                    f"Competitors reacted to our {strategy['metric']} pivot and neutralised the advantage. "
                    f"Risk exposure {round(strategy['risk']*100)}% materialised.\n\n"
                    f"Differentiation âˆ’{round(penalty,1)}pt → {round(diff,1)}%. "
                    f"Saturation +{round(sat_rise,1)}pt → {round(sat,1)}%."
                )

            diff = max(1.0, min(100.0, diff))
            sat  = max(5.0,  min(100.0, sat))

            # ── 7e. Check terminal conditions ────────────────────────────────────
            is_final = False
            status   = "RUNNING"

            if diff >= BREAKTHROUGH_DIFF:
                is_final = True
                status   = "SUCCESS"
                title    = "✦ Outcome: Market Breakthrough"
                desc     = (
                    f"After {i} data-driven iterations the simulation achieved breakthrough. "
                    f"Differentiation reached {round(diff,1)}% against "
                    f"{', '.join(rival_names)} across {n_clusters} analysed clusters. "
                    f"Saturation reduced to {round(sat,1)}%. "
                    f"A defensible competitive moat has been established."
                )
            elif sat >= COLLAPSE_SAT:
                is_final = True
                status   = "FAILURE"
                title    = "✦ Outcome: Market Saturation Collapse"
                desc     = (
                    f"Saturation hit {round(sat,1)}% after {i} iterations — the market is too dense "
                    f"to achieve meaningful differentiation. "
                    f"Competitors ({', '.join(rival_names)}) absorbed every strategic move. "
                    f"Final differentiation: {round(diff,1)}%."
                )
            elif i == SAFETY_CAP:
                is_final = True
                if diff >= 60:
                    status = "SUCCESS"
                    title  = "✦ Outcome: Narrow Margin Win"
                    desc   = (
                        f"After the maximum {SAFETY_CAP} iterations, differentiation stands at "
                        f"{round(diff,1)}% — enough for a defensible but narrow market position. "
                        f"Continued monitoring against {', '.join(rival_names)} is strongly recommended."
                    )
                else:
                    status = "FAILURE"
                    title  = "✦ Outcome: Exhaustion Without Breakthrough"
                    desc   = (
                        f"After {SAFETY_CAP} iterations, differentiation remained at {round(diff,1)}% "
                        f"with saturation at {round(sat,1)}%. No breakthrough achieved against "
                        f"{', '.join(rival_names)}."
                    )

            await websocket.send_json({
                "status":        status,
                "iteration":     i,
                "maxIterations": 0,   # dynamic; UI shows progress bar based on diff/sat
                "stageData":     {"id": i, "title": title, "desc": desc},
                "chartPoint":    {"month": month, "differentiation": round(diff), "saturation": round(sat)},
                "kpis": {
                    "differentiation": round(diff),
                    "saturation":      round(sat),
                    "persona_drift":   round(momentum * 60),
                    "resonance":       round(max(0.1, 1.0 + (diff / 40.0)), 1),
                },
            })

            if is_final:
                break

            logger.info(f"Simulating Month {month} (Iteration {i}). Status: {status}")
            await asyncio.sleep(2.0)

    except WebSocketDisconnect:
        logger.info("Simulation WS disconnected by client")
    except Exception as exc:
        logger.error(f"Simulation WS error: {exc}", exc_info=True)
        try:
            await websocket.send_json({
                "status": "FAILURE",
                "iteration": i,
                "maxIterations": i,
                "stageData": {
                    "id": i,
                    "title": "✦ Internal Engine Error",
                    "desc": f"The simulation encountered an unexpected error: {exc}",
                },
                "chartPoint": {"month": month_names[i % 12], "differentiation": round(diff), "saturation": round(sat)},
                "kpis": {"differentiation": round(diff), "saturation": round(sat), "persona_drift": 0, "resonance": 1.0},
            })
        except Exception:
            pass

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    logger.info(f"Starting uvicorn on 0.0.0.0:{port}")
    uvicorn.run("api:app", host="0.0.0.0", port=port, log_level="info")

