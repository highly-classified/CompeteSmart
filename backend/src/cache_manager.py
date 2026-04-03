from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime
import json
import logging
import re
from src import models

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
    fastest_growing = {"name": growth_res[0], "growth": growth_res[1]} if (growth_res and growth_res[0] and growth_res[0] != "N/A") else {"name": "Urban Company", "growth": 0}

    # --- Light Cleaning Utility ---
    def light_clean(label: str) -> str:
        if not label or label.lower().strip() == "n/a": return ""
        # 1. Strip numbers and ratings (e.g. 4.81, 61k reviews, trailing digits)
        label = re.sub(r'\(?\d+[\.\d]*[k]?\s*reviews\)?', '', label.lower())
        label = re.sub(r'\d+[\.\d]*', '', label)
        # 2. Add trim to 30 chars
        label = label[:30].strip(" .,;:-?!/")
        if label.lower() == "n/a": return ""
        return label.title()

    # --- Saturation Logic ---
    sat_query = """
    SELECT cl.label, COUNT(*) AS total
    FROM signals s JOIN clusters cl ON s.cluster_id = cl.id
    WHERE cl.label IS NOT NULL AND cl.label NOT ILIKE '%N/A%'
    GROUP BY cl.label ORDER BY total DESC LIMIT 1;
    """
    sat_res = db.execute(text(sat_query)).fetchone()
    sat_theme = light_clean(sat_res[0]) if sat_res and sat_res[0] else None
    if not sat_theme: sat_theme = "Cleaning" # Critical Fallback
    saturation = {"theme": sat_theme, "level": "high"}

    # --- Opportunity Logic ---
    opp_query = """
    SELECT cl.label, COUNT(*) AS total
    FROM signals s JOIN clusters cl ON s.cluster_id = cl.id
    WHERE cl.label IS NOT NULL AND cl.label NOT ILIKE '%N/A%'
    GROUP BY cl.label 
    HAVING COUNT(*) > 2
    ORDER BY total ASC LIMIT 1;
    """
    opp_res = db.execute(text(opp_query)).fetchone()
    opp_theme = light_clean(opp_res[0]) if opp_res and opp_res[0] else None
    if not opp_theme: opp_theme = "Pest Control" # Critical Fallback
    opportunity = {"theme": opp_theme, "level": "low"}


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

    # Themes (Aggregated by static clean labels)
    where_base = "WHERE cl.clean_label IS NOT NULL AND cl.clean_label != ''"
    if competitor != "ALL":
        where_base += " AND c.name = :comp"

    theme_query = f"""
    SELECT c.name, cl.clean_label, COUNT(*)
    FROM signals s 
    JOIN competitors c ON s.competitor_id = c.id
    JOIN clusters cl ON s.cluster_id = cl.id
    {where_base}
    GROUP BY 1, 2;
    """

    theme_res = db.execute(text(theme_query), params).fetchall()
    
    # Process and Limit
    themes = []
    comp_totals = {}
    for r in theme_res:
        comp_totals[r[0]] = comp_totals.get(r[0], 0) + r[2]

    for r in theme_res:
        comp_name = r[0]
        label_raw = r[1]
        count = r[2]
        total = comp_totals[comp_name]
        
        themes.append({
            "competitor": comp_name,
            "category": label_raw,
            "percentage": round((count * 100.0 / total), 2)
        })

    # Limit per competitor to top 6
    final_themes = []
    for comp in (["Urban Company", "Housejoy", "Sulekha"] if competitor == "ALL" else [competitor]):
        comp_themes = [t for t in themes if t["competitor"] == comp]
        final_themes.extend(sorted(comp_themes, key=lambda x: x["percentage"], reverse=True)[:6])
    
    themes = final_themes


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

    # Strength (Dynamic Pivot of Top 6 Segments)
    top_clusters_query = """
    SELECT cl.clean_label, COUNT(*) as total 
    FROM signals s JOIN clusters cl ON s.cluster_id = cl.id 
    WHERE cl.clean_label IS NOT NULL AND cl.clean_label != ''
    GROUP BY 1 ORDER BY 2 DESC LIMIT 6
    """
    top_clusters_res = db.execute(text(top_clusters_query)).fetchall()
    top_labels = [r[0] for r in top_clusters_res]

    if not top_labels:
        strength = []
    else:
        str_query = f"""
        SELECT c.name, cl.clean_label, COUNT(*) 
        FROM signals s 
        JOIN competitors c ON s.competitor_id = c.id 
        JOIN clusters cl ON s.cluster_id = cl.id
        WHERE cl.clean_label IN ({','.join([':l'+str(i) for i in range(len(top_labels))])})
        GROUP BY 1, 2;
        """
        str_params = {f"l{i}": label for i, label in enumerate(top_labels)}
        # Add :comp param if needed
        if competitor != "ALL":
            str_query = str_query.replace("WHERE", "WHERE c.name = :comp AND")
            str_params["comp"] = competitor
            
        str_res = db.execute(text(str_query), str_params).fetchall()
        
        strength_map = {}
        for r in str_res:
            comp_name, cluster_label, count = r[0], r[1], r[2]
            if comp_name not in strength_map:
                strength_map[comp_name] = {"name": comp_name}
            strength_map[comp_name][cluster_label] = float(count)
        
        strength = list(strength_map.values())


    return {
        "trend": trends,
        "themes": themes,
        "positioning": positioning,
        "whitespace": whitespace,
        "strength": strength
    }
