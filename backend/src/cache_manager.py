from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime
import logging
from collections import Counter, defaultdict
from src import models
from src.intelligence.temporal import TemporalEngine
from src.intelligence.advanced import AdvancedIntelligenceEngine
from src.trust_layer import compute_trust_score
import sys
import os

# Append parent dir to path to reach decision_layer.py if needed, 
# but usually PYTHONPATH handles this in the repo structure.
try:
    from decision_layer import process_decisions
except ImportError:
    # Fallback for different execution contexts
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    from decision_layer import process_decisions

logger = logging.getLogger("cache_manager")

# No runtime cleaning function needed anymore. 
# Labels are cleaned during the ingestion pipeline and stored in `clusters.clean_label`.


def refresh_dashboard_cache(db: Session):
    """
    Pre-computes all dashboard data and stores it in the DashboardCache table.
    This should be called after ingestion or via a scheduled job.
    """
    logger.info("Refreshing Dashboard Cache...")
    
    # 1. Summary Insights
    summary_data = compute_summary_insights(db)
    upsert_cache(db, "summary_insights", summary_data)
    
    # 2. Competitor Analysis (ALL)
    all_analysis = compute_competitor_analysis(db, "ALL")
    upsert_cache(db, "comp_analysis_ALL", all_analysis)
    
    # 3. Competitor Analysis (Individual)
    competitors = db.query(models.Competitor).all()
    for comp in competitors:
        comp_analysis = compute_competitor_analysis(db, comp.name)
        upsert_cache(db, f"comp_analysis_{comp.name}", comp_analysis)
        
    # 4. Suggested Experiments (NEW)
    logger.info("Refreshing Suggested Experiments...")
    experiments = compute_suggested_experiments(db)
    upsert_cache(db, "suggested_experiments", experiments)

    db.commit()
    logger.info("Dashboard Cache Refresh Complete.")

def upsert_cache(db: Session, key: str, data: dict):
    cache_entry = db.query(models.DashboardCache).filter(models.DashboardCache.key == key).first()
    if cache_entry:
        cache_entry.data = data
        cache_entry.last_updated = datetime.utcnow()
    else:
        cache_entry = models.DashboardCache(key=key, data=data)
        db.add(cache_entry)

def compute_summary_insights(db: Session):
    # Fastest Growing
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
    SELECT r.name, (r.cnt - COALESCE(p.cnt, 0)) AS growth
    FROM recent r LEFT JOIN previous p ON r.name = p.name
    ORDER BY growth DESC LIMIT 1;
    """

    label_rows = db.execute(text("""
        SELECT COALESCE(NULLIF(cl.clean_label, ''), cl.label) AS theme_label, COUNT(*) AS total
        FROM signals s
        JOIN clusters cl ON s.cluster_id = cl.id
        GROUP BY 1
    """)).fetchall()

    theme_counter = Counter()
    for raw_label, total in label_rows:
        theme_counter[normalize_theme_label(raw_label)] += int(total)

    ranked_themes = bucket_top_labels(theme_counter, top_n=5, include_others=False)
    saturation_theme = ranked_themes[0][0] if ranked_themes else "General Service"

    opportunity_candidates = [(label, total) for label, total in ranked_themes if total > 2]
    if not opportunity_candidates:
        opportunity_candidates = [(label, total) for label, total in theme_counter.items() if label != "General Service" and total > 2]
    opportunity_theme = min(opportunity_candidates, key=lambda item: item[1])[0] if opportunity_candidates else "General Service"

    saturation = {"theme": saturation_theme, "level": "high"}
    opportunity = {"theme": opportunity_theme, "level": "low"}
    
    # Growth (Already robust)
    growth_res = db.execute(text(growth_query)).fetchone()
    fastest_growing = {"name": growth_res[0], "growth": growth_res[1]} if (growth_res and growth_res[0] and growth_res[0] != "N/A") else {"name": "Urban Company", "growth": 0}

    # Clusters
    clusters_res = db.execute(text("SELECT COUNT(*) FROM clusters;")).fetchone()
    clusters_count = clusters_res[0] if clusters_res else 0

    return {
        "fastest_growing": fastest_growing,
        "saturation": saturation,
        "opportunity": opportunity,
        "clusters": {"count": clusters_count}
    }

def compute_competitor_analysis(db: Session, competitor: str):
    where_clause = "WHERE c.name = :comp" if competitor != "ALL" else ""
    params = {"comp": competitor} if competitor != "ALL" else {}

    # Trends
    trend_query = f"""
    SELECT c.name, TO_CHAR(DATE_TRUNC('month', ec.created_at), 'YYYY-MM'), COUNT(*)
    FROM extracted_content ec JOIN snapshots s ON ec.snapshot_id = s.id JOIN competitors c ON s.competitor_id = c.id
    {where_clause + (" AND " if where_clause else "WHERE ")} ec.created_at >= NOW() - INTERVAL '4 years'
    GROUP BY 1, 2 ORDER BY 2 ASC;
    """
    trend_res = db.execute(text(trend_query), params).fetchall()
    trends = [{"competitor": r[0], "month": r[1], "activity": float(r[2])} for r in trend_res]

    theme_query = f"""
    SELECT c.name, COALESCE(NULLIF(cl.clean_label, ''), cl.label) AS theme, COUNT(*)
    FROM signals s 
    JOIN competitors c ON s.competitor_id = c.id
    JOIN clusters cl ON s.cluster_id = cl.id
    {"WHERE c.name = :comp" if competitor != "ALL" else ""}
    GROUP BY 1, 2;
    """

    theme_res = db.execute(text(theme_query), params).fetchall()

    competitor_theme_counts = defaultdict(Counter)
    for comp_name, raw_label, count in theme_res:
        competitor_theme_counts[comp_name][normalize_theme_label(raw_label)] += int(count)

    themes = []
    for comp_name, counts in competitor_theme_counts.items():
        total = sum(counts.values())
        if total <= 0:
            continue

        for label, value in bucket_top_labels(counts, top_n=5, include_others=True):
            themes.append({
                "competitor": comp_name,
                "category": label,
                "percentage": round((value * 100.0 / total), 2)
            })


    # Pos
    pos_query = f"""
    WITH counts AS (SELECT c.name, COUNT(*) AS total FROM extracted_content ec JOIN snapshots s ON ec.snapshot_id = s.id JOIN competitors c ON s.competitor_id = c.id {where_clause} GROUP BY 1),
    max_val AS (SELECT MAX(total) AS max_total FROM counts)
    SELECT c.name, ROUND((c.total * 10.0 / m.max_total), 2) FROM counts c, max_val m;
    """
    pos_res = db.execute(text(pos_query), params).fetchall()
    mock_pos = {"Urban Company": {"p": 8.5, "t": 9.0}, "Housejoy": {"p": 6.0, "t": 6.5}, "Sulekha": {"p": 4.0, "t": 5.0}}
    positioning = [{"competitor": r[0], "activity_score": float(r[1]), "price_index": mock_pos.get(r[0], {"p":5,"t":5})["p"], "trust_score": mock_pos.get(r[0], {"p":5,"t":5})["t"]} for r in pos_res]

    # Whitespace Opportunities (Metrics Fix)
    where_signals = "WHERE c.name = :comp" if competitor != "ALL" else ""
    white_query = f"""
    SELECT 
        c.name AS competitor,
        COUNT(*) FILTER (WHERE s.created_at >= NOW() - INTERVAL '30 days') AS recent_count,
        COUNT(*) FILTER (WHERE s.created_at < NOW() - INTERVAL '30 days') AS past_count,
        COUNT(*) AS total_count
    FROM signals s
    JOIN competitors c ON s.competitor_id = c.id
    {where_signals}
    GROUP BY c.name;
    """
    white_res = db.execute(text(white_query), params).fetchall()
    
    max_total = max([r[3] for r in white_res]) if white_res else 1
    
    whitespace = []
    for r in white_res:
        comp_name, recent, past, total = r[0], r[1], r[2], r[3]
        
        # Rule: Ignore < 3 signals
        if total < 3: continue
        
        # X: Competition Score (Normalized 0 to 1)
        x_score = round(total / max_total, 2)
        
        # Y: Growth Score (Last 30d vs Previous)
        growth = (recent - past) / (past + 1)
        y_score = round(max(-1, min(1, growth)), 2) # Clamped between -1 and 1
        
        whitespace.append({
            "competitor": comp_name,
            "x": x_score,
            "y": y_score
        })

    # Strength (Dynamic Pivot of Top Themes)
    global_theme_counter = Counter()
    for counts in competitor_theme_counts.values():
        global_theme_counter.update(counts)
    top_labels = [label for label, _ in bucket_top_labels(global_theme_counter, top_n=5, include_others=False)]

    strength = []
    if top_labels:
        for comp_name, counts in competitor_theme_counts.items():
            row = {"name": comp_name}
            has_value = False
            for label in top_labels:
                value = float(counts.get(label, 0))
                if value > 0:
                    has_value = True
                row[label] = value
            if has_value:
                strength.append(row)


    return {
        "trend": trends,
        "themes": themes,
        "positioning": positioning,
        "whitespace": whitespace,
        "strength": strength
    }

def compute_suggested_experiments(db: Session):
    """
    Consolidates intelligence insights and runs the decision layer to generate
    recommended experiments, then persists them to the cache.
    """
    try:
        # 1. Gather Intelligence Data
        temp_engine = TemporalEngine(db)
        trends = temp_engine.calculate_trends()
        saturations = temp_engine.calculate_saturation()
        
        adv_engine = AdvancedIntelligenceEngine(db)
        whitespaces = adv_engine.detect_whitespace()
        
        # 2. Consolidate into Insights for Decision Layer
        insights = []
        for t in trends:
            c_id = t["cluster_id"]
            # Find matching saturation mapping
            s_match = next((s for s in saturations if s["cluster_id"] == c_id), None)
            sat_score = s_match["saturation_score"] if s_match else 0.0
            
            # Map detected whitespace vectors into themes (logic from prototype_pipeline)
            # In production this can be further refined
            w_personas = ["budget-conscious", "untapped-niche"] if whitespaces else []
            
            insights.append({
                "cluster_id": c_id,
                "cluster_name": t["cluster_label"] or "Untitled Cluster",
                "trend": t["growth_rate"],
                "saturation": sat_score,
                "whitespace_personas": w_personas
            })
            
        if not insights:
            logger.warning("No insights found to generate experiments.")
            return []

        # 3. Run Decision Layer
        decisions = process_decisions(insights)
        
        # 4. Enrich with Trust & Risk Layer
        final_experiments = []
        for decision in decisions:
            cluster_id = decision["cluster_id"]
            experiment_text = decision["experiment"]
            
            try:
                trust_output = compute_trust_score(
                    cluster_id=cluster_id, 
                    experiment=experiment_text, 
                    client_positioning="premium"
                )
            except Exception as e:
                logger.error(f"Trust score calculation failed for {cluster_id}: {e}")
                trust_output = {"risk_score": 0.5, "risk_level": "medium", "explanation": "Trust calculation failed."}
            
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
            
        return final_experiments
        
    except Exception as e:
        logger.error(f"Failed to compute suggested experiments: {e}")
        return []
