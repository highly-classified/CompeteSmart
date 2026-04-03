from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime
from typing import Any
import logging
import math
import re
from collections import Counter, defaultdict
from src import models
from src.labeling import bucket_top_labels, normalize_theme_label
from src.intelligence.temporal import TemporalEngine
from src.intelligence.advanced import AdvancedIntelligenceEngine
from src.experiment_generator import generate_experiment_output
from src.ml_decision_layer import generate_ranked_experiment_candidates
from src.trust_layer import compute_trust_score

logger = logging.getLogger("cache_manager")

# No runtime cleaning function needed anymore. 
# Labels are cleaned during the ingestion pipeline and stored in `clusters.clean_label`.

RATING_PATTERN = re.compile(r"rating[:\s]+([0-5](?:\.\d+)?)", re.IGNORECASE)
PRICE_MARKERS = (
    "price", "pricing", "discount", "offer", "budget", "affordable",
    "value", "cost", "starting at", "₹", "rs ", "under ", "only "
)
REVIEW_MARKERS = (
    "review", "reviews", "rating", "rated", "feedback", "experience",
    "top-rated", "verified", "reliable", "professional"
)


def _clamp_score(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def _cluster_signal_context(db: Session, cluster_id: str) -> dict:
    rows = (
        db.query(models.Signal.content, models.Signal.confidence)
        .filter(models.Signal.cluster_id == cluster_id)
        .order_by(models.Signal.confidence.desc(), models.Signal.created_at.desc(), models.Signal.id.desc())
        .all()
    )

    contents = [row[0] for row in rows if row[0]]
    evidence_count = len(contents)
    avg_signal_confidence = (
        sum(float(row[1]) for row in rows if row[1] is not None) / len(rows)
        if rows else 0.5
    )
    avg_signal_confidence = _clamp_score(avg_signal_confidence)

    price_hits = 0
    review_hits = 0
    ratings = []
    for content in contents:
        lowered = content.lower()
        price_hits += sum(1 for marker in PRICE_MARKERS if marker in lowered)
        review_hits += sum(1 for marker in REVIEW_MARKERS if marker in lowered)
        match = RATING_PATTERN.search(content)
        if match:
            try:
                ratings.append(float(match.group(1)) / 5.0)
            except (TypeError, ValueError):
                continue

    price_density = _clamp_score(price_hits / max(evidence_count * 2, 1))
    avg_rating_score = sum(ratings) / len(ratings) if ratings else 0.0
    review_density = _clamp_score(review_hits / max(evidence_count * 2, 1))
    review_signal_strength = _clamp_score(
        (avg_rating_score * 0.55)
        + (review_density * 0.25)
        + (avg_signal_confidence * 0.20)
    )

    return {
        "evidence_count": evidence_count,
        "evidence": contents[:5],
        "avg_signal_confidence": round(avg_signal_confidence, 3),
        "price_signal_strength": round(price_density, 3),
        "review_signal_strength": round(review_signal_strength, 3),
        "avg_rating": round(avg_rating_score * 5.0, 2) if ratings else None,
        "review_signal_count": review_hits,
        "evidence_strength": round(
            _clamp_score(math.log1p(evidence_count) / math.log1p(12)) if evidence_count > 0 else 0.0,
            3,
        ),
    }


def _get_target_competitors(db: Session, competitor: str) -> list[str]:
    query = db.query(models.Competitor.name)
    if competitor != "ALL":
        query = query.filter(models.Competitor.name == competitor)
    return [row[0] for row in query.order_by(models.Competitor.name.asc()).all()]


def _load_competitor_theme_counts(db: Session, competitor: str) -> tuple[list[str], dict[str, Counter]]:
    competitor_names = _get_target_competitors(db, competitor)
    params = {"comp": competitor} if competitor != "ALL" else {}

    theme_query = f"""
    SELECT c.name, COALESCE(NULLIF(cl.clean_label, ''), cl.label) AS theme, COUNT(*) AS total
    FROM signals s
    JOIN competitors c ON s.competitor_id = c.id
    JOIN clusters cl ON s.cluster_id = cl.id
    {"WHERE c.name = :comp" if competitor != "ALL" else ""}
    GROUP BY c.name, theme;
    """

    theme_res = db.execute(text(theme_query), params).fetchall()

    competitor_theme_counts = {name: Counter() for name in competitor_names}
    for comp_name, raw_label, count in theme_res:
        competitor_theme_counts.setdefault(comp_name, Counter())
        competitor_theme_counts[comp_name][normalize_theme_label(raw_label)] += int(count)

    return competitor_names, competitor_theme_counts


def _build_theme_distribution(
    competitor_names: list[str],
    competitor_theme_counts: dict[str, Counter],
) -> tuple[list[dict], dict[str, list[dict]], dict[str, dict[str, float]]]:
    themes = []
    theme_groups = {}
    normalized_scores = {}

    for comp_name in competitor_names:
        counts = competitor_theme_counts.get(comp_name, Counter())
        total = sum(counts.values())
        normalized_scores[comp_name] = {}

        if total <= 0:
            theme_groups[comp_name] = []
            continue

        grouped = []
        for label, value in bucket_top_labels(counts, top_n=5, include_others=True):
            percentage = round((value * 100.0 / total), 2)
            entry = {
                "competitor": comp_name,
                "category": label,
                "percentage": percentage,
            }
            grouped.append(entry)
            themes.append(entry)
            normalized_scores[comp_name][label] = percentage

        theme_groups[comp_name] = grouped

    return themes, theme_groups, normalized_scores


def _build_strength_distribution(
    competitor_names: list[str],
    competitor_theme_counts: dict[str, Counter],
) -> tuple[list[dict], list[dict], list[str]]:
    normalized_share_sums = Counter()
    normalized_theme_scores = {}

    for comp_name in competitor_names:
        counts = competitor_theme_counts.get(comp_name, Counter())
        total = sum(counts.values())
        normalized_theme_scores[comp_name] = {}
        if total <= 0:
            continue

        for label, value in counts.items():
            score = round(value / total, 6)
            normalized_theme_scores[comp_name][label] = score
            normalized_share_sums[label] += score

    top_labels = [label for label, _ in bucket_top_labels(normalized_share_sums, top_n=5, include_others=False)]

    strength = []
    strength_groups = []
    for comp_name in competitor_names:
        counts = competitor_theme_counts.get(comp_name, Counter())
        total = sum(counts.values())
        row = {"name": comp_name}
        segments = []
        others_share = 0.0

        if total > 0:
            for label, score in normalized_theme_scores.get(comp_name, {}).items():
                if label not in top_labels:
                    others_share += score

        for label in top_labels:
            normalized_value = round(normalized_theme_scores.get(comp_name, {}).get(label, 0.0) * 100, 2)
            row[label] = normalized_value
            segments.append({"label": label, "value": normalized_value})

        if others_share > 0:
            others_value = round(others_share * 100, 2)
            row["Others"] = others_value
            segments.append({"label": "Others", "value": others_value})
        elif top_labels:
            row["Others"] = 0.0

        strength.append(row)
        strength_groups.append({
            "competitor": comp_name,
            "segments": segments,
        })

    return strength, strength_groups, top_labels


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

def upsert_cache(db: Session, key: str, data: Any):
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
    competitor_names, competitor_theme_counts = _load_competitor_theme_counts(db, competitor)

    # Trends
    trend_query = f"""
    SELECT c.name, TO_CHAR(DATE_TRUNC('month', ec.created_at), 'YYYY-MM'), COUNT(*)
    FROM extracted_content ec JOIN snapshots s ON ec.snapshot_id = s.id JOIN competitors c ON s.competitor_id = c.id
    {where_clause + (" AND " if where_clause else "WHERE ")} ec.created_at >= NOW() - INTERVAL '4 years'
    GROUP BY 1, 2 ORDER BY 2 ASC;
    """
    trend_res = db.execute(text(trend_query), params).fetchall()
    trends = [{"competitor": r[0], "month": r[1], "activity": float(r[2])} for r in trend_res]

    themes, theme_groups, _ = _build_theme_distribution(competitor_names, competitor_theme_counts)


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

    # Strength (Normalized per competitor so high-volume brands do not dominate)
    strength, strength_groups, strength_labels = _build_strength_distribution(
        competitor_names,
        competitor_theme_counts,
    )


    return {
        "trend": trends,
        "themes": themes,
        "theme_groups": theme_groups,
        "positioning": positioning,
        "whitespace": whitespace,
        "strength": strength,
        "strength_groups": strength_groups,
        "strength_labels": strength_labels,
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
            signal_context = _cluster_signal_context(db, c_id)
            
            # Map detected whitespace vectors into themes (logic from prototype_pipeline)
            # In production this can be further refined
            w_personas = ["budget-conscious", "untapped-niche"] if whitespaces else []
            
            insights.append({
                "cluster_id": c_id,
                "cluster_name": t["cluster_label"] or "Untitled Cluster",
                "trend": t["growth_rate"],
                "saturation": sat_score,
                "whitespace_personas": w_personas,
                **signal_context,
            })
            
        if not insights:
            logger.warning("No insights found to generate experiments.")
            return []

        # 3. Run ML -> Decision Engine pipeline
        ranked_candidates = generate_ranked_experiment_candidates(insights)
        
        # 4. Enrich with Trust & Risk Layer + structured experiment generation
        final_experiments = []
        for candidate in ranked_candidates:
            cluster_id = candidate["cluster_id"]
            ml_analysis = candidate["ml_analysis"]
            category = candidate["cluster_name"]
            experiment_text = generate_experiment_output(
                candidate,
                ml_analysis,
                candidate["decision_type"],
                {"risk_score": 0.5, "risk_level": "medium"},
            )["experiment"]
            
            try:
                trust_output = compute_trust_score(
                    cluster_id=cluster_id, 
                    experiment=experiment_text, 
                    client_positioning="premium"
                )
            except Exception as e:
                logger.error(f"Trust score calculation failed for {cluster_id}: {e}")
                trust_output = {
                    "risk_score": 0.5,
                    "risk_level": "medium",
                    "confidence_score": 0.4,
                    "success_score": 0.4,
                    "explanation": "Trust calculation failed.",
                    "traceability": {
                        "total_signals": 0,
                        "sample_signals": [],
                        "competitor_ids": [],
                    },
                }
            
            structured_experiment = generate_experiment_output(
                candidate,
                ml_analysis,
                candidate["decision_type"],
                trust_output,
            )
            structured_experiment.update({
                "cluster_id": cluster_id,
                "cluster_name": category,
                "evidence": candidate.get("evidence", []),
                "decision": {
                    "priority_score": candidate.get("priority_score"),
                    "experiment_type": candidate.get("decision_type"),
                    "ml_score": ml_analysis.get("prediction_score"),
                    "model_family": ml_analysis.get("model_family"),
                },
            })
            print("Generated Experiment:", structured_experiment)
            final_experiments.append(structured_experiment)
            
        return final_experiments
        
    except Exception as e:
        logger.error(f"Failed to compute suggested experiments: {e}")
        return []
