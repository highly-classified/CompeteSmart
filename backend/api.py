from fastapi import FastAPI, Depends, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text, func
from src.database import get_db, engine, SessionLocal
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
import asyncio
import random
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from src.cache_manager import refresh_dashboard_cache, compute_summary_insights, compute_competitor_analysis
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
    "http://localhost:3001",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "https://compete-smart.vercel.app"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=r"http://localhost:\d+",
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
            models.Cluster.clean_label.label("cluster_name"),
            func.to_char(models.Snapshot.created_at, "YYYY-MM").label("month"),
            func.count(models.Signal.id).label("count")
        )
        .join(models.Snapshot, models.Signal.snapshot_id == models.Snapshot.id)
        .join(models.Competitor, models.Signal.competitor_id == models.Competitor.id)
        .join(models.Cluster, models.Signal.cluster_id == models.Cluster.id)
        .filter(models.Competitor.client_id == client_id)
        .filter(models.Cluster.clean_label != "")
        .filter(models.Signal.cluster_id.isnot(None))
        .group_by(models.Cluster.clean_label, "month")
        .order_by(models.Cluster.clean_label, "month")
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
            func.count(models.Signal.id).filter(models.Cluster.clean_label.op("~*")(premium_p)).label("premium"),
            func.count(models.Signal.id).filter(models.Cluster.clean_label.op("~*")(affordable_p)).label("affordable"),
            func.count(models.Signal.id).filter(models.Cluster.clean_label.op("~*")(outcome_p)).label("outcome"),
            func.count(models.Signal.id).filter(models.Cluster.clean_label.op("~*")(feature_p)).label("feature")
        )
        .join(models.Signal, models.Competitor.id == models.Signal.competitor_id)
        .join(models.Cluster, models.Signal.cluster_id == models.Cluster.id)
        .filter(models.Competitor.client_id == client_id)
        .filter(models.Cluster.clean_label != "")
        .group_by(models.Competitor.name)
        .all()
    )

    # Get dominant cluster per competitor
    # This is a bit more complex in a single query, so we'll do a separate one or just pick the top from another join
    dominant_clusters = (
        db.query(
            models.Competitor.name,
            models.Cluster.clean_label.label("top_cluster")
        )
        .join(models.Signal, models.Competitor.id == models.Signal.competitor_id)
        .join(models.Cluster, models.Signal.cluster_id == models.Cluster.id)
        .filter(models.Competitor.client_id == client_id)
        .filter(models.Cluster.clean_label != "")
        .group_by(models.Competitor.name, models.Cluster.clean_label)
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
            models.Cluster.clean_label.label("name"),
            func.count(models.Signal.id).label("count")
        )
        .join(models.Signal, models.Cluster.id == models.Signal.cluster_id)
        .join(models.Competitor, models.Signal.competitor_id == models.Competitor.id)
        .filter(models.Competitor.client_id == client_id)
        .filter(models.Cluster.clean_label != "")
        .group_by(models.Cluster.clean_label)
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
def trigger_cache_refresh(db: Session = Depends(get_db)):
    """Force rebuild the entire dashboard cache"""
    refresh_dashboard_cache(db)
    return {"status": "success", "message": "Dashboard cache rebuilt"}

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
async def simulate_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    # ── 1. LOAD REAL DATA FROM DATABASE ──
    db = SessionLocal()
    try:
        # Fetch all competitors
        competitors = db.query(models.Competitor).all()
        competitor_names = [c.name for c in competitors] if competitors else ["Unknown Competitor"]
        
        # Fetch clusters with their real saturation and trend data
        temp_engine = TemporalEngine(db)
        real_saturations = temp_engine.calculate_saturation()
        real_trends = temp_engine.calculate_trends()
        
        # Build cluster intelligence map
        cluster_intel = {}
        for s in real_saturations:
            cid = s["cluster_id"]
            cluster_intel[cid] = {
                "clean_label": s.get("cluster_label", "Unknown Theme"),
                "saturation": s.get("saturation_score", 0.5),
                "competitors_using": s.get("competitors_using", 1),
                "total_competitors": s.get("total_competitors", 3),
            }
        for t in real_trends:
            cid = t["cluster_id"]
            if cid in cluster_intel:
                cluster_intel[cid]["growth_rate"] = t.get("growth_rate", 0.0)
                cluster_intel[cid]["trend"] = t.get("trend", "stable")
                cluster_intel[cid]["signal_count"] = t.get("current_count", 0)
        
        # Pick the top clusters by saturation (most interesting for simulation)
        sorted_clusters = sorted(cluster_intel.values(), key=lambda x: x.get("saturation", 0), reverse=True)
        target_clusters = sorted_clusters[:8] if len(sorted_clusters) >= 8 else sorted_clusters
        
        # Load decision layer experiments (if available)
        decision_experiments = []
        try:
            with open("decision_layer_output.json", "r") as f:
                decision_experiments = json.load(f)
        except Exception:
            pass
        
        # ── 2. COMPUTE INITIAL CONDITIONS FROM REAL DATA ──
        if target_clusters:
            avg_saturation = sum(c.get("saturation", 0.5) for c in target_clusters) / len(target_clusters)
            avg_growth = sum(c.get("growth_rate", 0.0) for c in target_clusters) / len(target_clusters)
        else:
            avg_saturation = 0.5
            avg_growth = 0.0
        
        # Starting saturation is derived from REAL average saturation (scaled to 0-100)
        sat = round(min(95, max(40, avg_saturation * 100)), 1)
        # Starting differentiation is inversely related to saturation
        diff = round(min(40, max(5, (1.0 - avg_saturation) * 50)), 1)
        
    except Exception as e:
        logger.error(f"Failed to load real data for simulation: {e}")
        competitor_names = ["Competitor A", "Competitor B"]
        target_clusters = []
        decision_experiments = []
        sat = 75.0
        diff = 20.0
    finally:
        db.close()
    
    # ── 3. BUILD DATA-DRIVEN STRATEGIES ──
    max_iterations = 8
    momentum = 0.0
    month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    
    # Dynamically build strategies using real cluster & competitor names
    rival_1 = competitor_names[0] if len(competitor_names) > 0 else "leading competitor"
    rival_2 = competitor_names[1] if len(competitor_names) > 1 else "secondary competitor"
    rival_3 = competitor_names[2] if len(competitor_names) > 2 else "emerging competitor"
    
    # Pick real cluster labels for contextual text
    cl_labels = [c.get("clean_label", "market segment")[:60] for c in target_clusters]
    cl1 = cl_labels[0] if len(cl_labels) > 0 else "primary market segment"
    cl2 = cl_labels[1] if len(cl_labels) > 1 else "secondary market segment"
    cl3 = cl_labels[2] if len(cl_labels) > 2 else "emerging vertical"
    
    # Risk is derived from how many competitors are in that cluster
    def cluster_risk(idx):
        if idx < len(target_clusters):
            c = target_clusters[idx]
            using = c.get("competitors_using", 1)
            total = c.get("total_competitors", 3)
            return min(0.65, max(0.30, using / max(total, 1)))
        return 0.45

    strategies = [
        {"name": f"Premium Positioning vs {rival_1}", "diff_boost": (18, 35), "sat_reduce": (8, 18), "risk": cluster_risk(0),
         "success_text": f"Premium feature rollout resonated in '{cl1}'. {rival_1} cannot replicate the proprietary tech stack within this cycle. High-value segments shifting.",
         "fail_text": f"Premium positioning in '{cl1}' backfired — {rival_1}'s brand loyalty proved too strong. Target audience perceives insufficient value delta."},
        {"name": f"Aggressive Undercut in '{cl2[:30]}'", "diff_boost": (10, 22), "sat_reduce": (12, 25), "risk": cluster_risk(1),
         "success_text": f"Price disruption in '{cl2}' forced {rival_2} into margin pressure. Budget-conscious users are migrating at scale.",
         "fail_text": f"Price war triggered in '{cl2}' — {rival_2} matched pricing within 48 hours. Saturation intensified across all segments."},
        {"name": f"Whitespace Niche: '{cl3[:30]}'", "diff_boost": (20, 40), "sat_reduce": (5, 15), "risk": cluster_risk(2),
         "success_text": f"Captured underserved micro-segment '{cl3}'. Zero direct competition detected. First-mover advantage established.",
         "fail_text": f"The niche '{cl3}' proved too narrow for sustainable growth. Customer acquisition cost exceeds lifetime value."},
        {"name": "AI-Driven Personalization Engine", "diff_boost": (15, 30), "sat_reduce": (10, 20), "risk": 0.40,
         "success_text": f"AI personalization deployed across user base. Engagement up 340%. {rival_1} and {rival_2} lack data infrastructure to replicate.",
         "fail_text": f"Personalization model underfitting — users report irrelevant recommendations. {rival_1} already has a stronger data moat."},
        {"name": f"Community-Led Growth vs {rival_2}", "diff_boost": (12, 25), "sat_reduce": (8, 16), "risk": 0.48,
         "success_text": f"Organic community flywheel activated. User-generated content now drives 60% of new acquisition. Defensible moat established against {rival_2}.",
         "fail_text": f"Community engagement stalled. Users prefer {rival_2}'s established ecosystem. Network effects working against us."},
        {"name": f"Strategic Partnership Play", "diff_boost": (15, 28), "sat_reduce": (10, 22), "risk": 0.42,
         "success_text": f"Partnership secured exclusive distribution channel in '{cl1}'. {rival_3} access blocked for 18-month exclusivity window.",
         "fail_text": f"Partnership negotiations collapsed. {rival_1} secured the deal instead, strengthening their position in '{cl1}'."},
        {"name": "Rapid Feature Innovation Sprint", "diff_boost": (18, 32), "sat_reduce": (6, 14), "risk": 0.52,
         "success_text": f"Feature velocity outpaced all {len(competitor_names)} tracked competitors 3:1. Market perception shifted to innovation leader positioning.",
         "fail_text": f"Feature bloat detected. Core product quality degraded. {rival_1} capitalized on our instability."},
        {"name": f"Brand Narrative Overhaul", "diff_boost": (14, 26), "sat_reduce": (10, 20), "risk": 0.46,
         "success_text": f"New brand narrative achieved viral resonance against {rival_1}. Share-of-voice increased 280%. Competitors forced to react defensively.",
         "fail_text": f"Brand repositioning confused existing customer base. Trust metrics declined. {rival_2} exploited the transition gap."},
    ]
    
    success_verdicts = [
        f"The iterative simulation achieved market breakthrough against {', '.join(competitor_names[:3])}. Differentiation score exceeded 80%, establishing a defensible competitive moat across {len(target_clusters)} analyzed market clusters.",
        "Simulation complete — SUCCESS. The agentic pivot engine identified a viable path through {attempts} strategic iterations. Final differentiation of {diff}% with saturation reduced to {sat}% indicates a strong, sustainable market position.",
    ]
    
    failure_verdicts = [
        f"SIMULATION EXHAUSTED: After {{attempts}} strategic pivots against {rival_1} and {rival_2}, the market proved too saturated for differentiation. All viable strategies were attempted but competitor reaction speed prevented breakthrough.",
        "FATAL OUTCOME: The simulation ran {attempts} iterations without achieving escape velocity. Current saturation at {sat}% is unsustainable. The competitive landscape across {len_clusters} clusters is too dense for incremental strategies.".replace("{len_clusters}", str(len(target_clusters))),
    ]

    used_strategies = []

    try:
        # ── Stage 0: Data-Driven Initialization ──
        init_desc = (
            f"Loaded {len(target_clusters)} market clusters, {len(competitor_names)} competitors "
            f"({', '.join(competitor_names[:3])}), and {len(decision_experiments)} experiment recommendations. "
            f"Real-time market saturation: {sat}%. Starting differentiation baseline: {diff}%."
        )
        
        await websocket.send_json({
            "status": "RUNNING",
            "iteration": 0,
            "maxIterations": max_iterations,
            "stageData": {
                "id": 0,
                "title": "Initializing with Real Market Data",
                "desc": init_desc,
            },
            "chartPoint": {"month": month_names[0], "differentiation": round(diff), "saturation": round(sat)},
            "kpis": {"differentiation": round(diff), "saturation": round(sat), "persona_drift": 0, "resonance": 1.0}
        })
        
        await asyncio.sleep(2.5)

        for i in range(1, max_iterations + 1):
            month = month_names[i % 12]
            
            # Pick a strategy we haven't used yet
            available = [s for s in strategies if s["name"] not in used_strategies]
            if not available:
                available = strategies
            strategy = random.choice(available)
            used_strategies.append(strategy["name"])
            
            # ── Data-Driven Probability Engine ──
            base_chance = 1.0 - strategy["risk"]
            momentum_bonus = min(momentum * 0.08, 0.2)
            saturation_penalty = max((sat - 70) * 0.005, 0)
            success_chance = min(max(base_chance + momentum_bonus - saturation_penalty, 0.15), 0.85)
            
            roll = random.random()
            succeeded = roll < success_chance
            
            if succeeded:
                boost = random.randint(*strategy["diff_boost"])
                reduction = random.randint(*strategy["sat_reduce"])
                diff += boost
                sat -= reduction
                momentum += 0.5
                title = f"Attempt {i}: {strategy['name']} ✓"
                desc = strategy["success_text"]
            else:
                penalty = random.randint(2, 12)
                increase = random.randint(3, 10)
                diff -= penalty
                sat += increase
                momentum = max(momentum - 0.3, 0)
                title = f"Attempt {i}: {strategy['name']} ✗"
                desc = strategy["fail_text"] + " Pivoting to next strategy..."
                
            diff = max(5, min(100, diff))
            sat = max(10, min(100, sat))
            
            # ── Win/Loss Evaluation ──
            status = "RUNNING"
            is_final = False
            
            if diff >= 80:
                is_final = True
                status = "SUCCESS"
                title = "✦ Outcome: Market Domination"
                desc = random.choice(success_verdicts).format(attempts=i, diff=round(diff), sat=round(sat))
            elif sat >= 95:
                is_final = True
                status = "FAILURE"
                title = "✦ Outcome: Strategic Collapse"
                desc = random.choice(failure_verdicts).format(attempts=i, diff=round(diff), sat=round(sat))
            elif i == max_iterations:
                is_final = True
                if diff >= 60:
                    status = "SUCCESS"
                    title = "✦ Outcome: Marginal Victory"
                    desc = f"After {i} iterations against {rival_1} and {rival_2}, differentiation reached {round(diff)}% — sufficient for a defensible but narrow position. Continued monitoring recommended."
                else:
                    status = "FAILURE"
                    title = "✦ Outcome: Exhaustion"
                    desc = random.choice(failure_verdicts).format(attempts=i, diff=round(diff), sat=round(sat))

            await websocket.send_json({
                "status": status,
                "iteration": i,
                "maxIterations": max_iterations,
                "stageData": {
                    "id": i,
                    "title": title,
                    "desc": desc,
                },
                "chartPoint": {"month": month, "differentiation": round(diff), "saturation": round(sat)},
                "kpis": {
                    "differentiation": round(diff), 
                    "saturation": round(sat), 
                    "persona_drift": round(momentum * 60), 
                    "resonance": round(1.0 + (diff / 40), 1)
                }
            })

            if is_final:
                break
                
            await asyncio.sleep(3.0)
            
    except WebSocketDisconnect:
        logger.info("Simulation websocket disconnected by client")
    except Exception as e:
        logger.error(f"Simulation WS error: {e}")
        try:
            await websocket.close()
        except:
            pass

if __name__ == "__main__":
    import uvicorn
    # Render provides the port in the PORT environment variable
    port = int(os.environ.get("PORT", 8000))
    logger.info(f"Starting uvicorn on 0.0.0.0:{port}")
    # Bind to 0.0.0.0 so the service is accessible externally
    uvicorn.run("api:app", host="0.0.0.0", port=port, log_level="info")
