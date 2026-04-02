from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime
import json
import logging
from src import models

logger = logging.getLogger("cache_manager")

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
    growth_res = db.execute(text(growth_query)).fetchone()
    fastest_growing = {"name": growth_res[0], "growth": growth_res[1]} if growth_res else {"name": "N/A", "growth": 0}

    # Saturation
    sat_query = """
    SELECT cl.label AS theme, COUNT(*) AS density
    FROM signals s JOIN clusters cl ON s.cluster_id = cl.id
    WHERE s.cluster_id IS NOT NULL
    GROUP BY cl.label ORDER BY density DESC LIMIT 1;
    """
    sat_res = db.execute(text(sat_query)).fetchone()
    saturation = {"theme": sat_res[0] if sat_res else "N/A", "level": "high"}

    # Opportunity
    opp_query = """
    SELECT cl.label AS theme, COUNT(*) AS density
    FROM signals s JOIN clusters cl ON s.cluster_id = cl.id
    WHERE s.cluster_id IS NOT NULL
    GROUP BY cl.label ORDER BY density ASC LIMIT 1;
    """
    opp_res = db.execute(text(opp_query)).fetchone()
    opportunity = {"theme": opp_res[0] if opp_res else "N/A", "level": "low"}

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

    # Themes
    theme_query = f"""
    SELECT c.name, s.category, ROUND((COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (PARTITION BY c.name)), 2)
    FROM signals s JOIN competitors c ON s.competitor_id = c.id
    {where_clause} GROUP BY 1, 2;
    """
    theme_res = db.execute(text(theme_query), params).fetchall()
    themes = [{"competitor": r[0], "category": r[1] or "General", "percentage": float(r[2])} for r in theme_res]

    # Pos
    pos_query = f"""
    WITH counts AS (SELECT c.name, COUNT(*) AS total FROM extracted_content ec JOIN snapshots s ON ec.snapshot_id = s.id JOIN competitors c ON s.competitor_id = c.id {where_clause} GROUP BY 1),
    max_val AS (SELECT MAX(total) AS max_total FROM counts)
    SELECT c.name, ROUND((c.total * 10.0 / m.max_total), 2) FROM counts c, max_val m;
    """
    pos_res = db.execute(text(pos_query), params).fetchall()
    mock_pos = {"Urban Company": {"p": 8.5, "t": 9.0}, "Housejoy": {"p": 6.0, "t": 6.5}, "Sulekha": {"p": 4.0, "t": 5.0}}
    positioning = [{"competitor": r[0], "activity_score": float(r[1]), "price_index": mock_pos.get(r[0], {"p":5,"t":5})["p"], "trust_score": mock_pos.get(r[0], {"p":5,"t":5})["t"]} for r in pos_res]

    # Whitespace
    white_query = f"""
    WITH cs AS (SELECT c.name, COUNT(ec.id) AS activity FROM extracted_content ec JOIN snapshots s ON ec.snapshot_id = s.id JOIN competitors c ON s.competitor_id = c.id {where_clause} GROUP BY 1)
    SELECT name, activity * 100.0 / MAX(activity) OVER (), RANDOM() * 100 FROM cs;
    """
    # Fix: cs table in with has 'competitor' not 'name' in current api.py logic, but I'll use r[0]
    white_res = db.execute(text(white_query), params).fetchall()
    whitespace = [{"name": r[0], "x": float(r[1]), "y": float(r[2])} for r in white_res]

    # Strength
    str_query = f"""
    SELECT c.name, s.category, COUNT(*) FROM signals s JOIN competitors c ON s.competitor_id = c.id {where_clause} GROUP BY 1, 2;
    """
    str_res = db.execute(text(str_query), params).fetchall()
    strength = [{"name": r[0], "category": r[1] or "Other", "score": float(r[2])} for r in str_res]

    return {
        "trend": trends,
        "themes": themes,
        "positioning": positioning,
        "whitespace": whitespace,
        "strength": strength
    }
