import os
import psycopg2
from psycopg2.extras import DictCursor
from typing import Dict, Any
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def compute_trust_score(cluster_id: str, experiment: str, client_positioning: str) -> dict:
    """
    Computes a risk score for a given experiment based on market signals and trends.
    """
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        raise ValueError("DATABASE_URL environment variable is missing.")

    conn = None
    try:
        conn = psycopg2.connect(db_url)
        with conn.cursor(cursor_factory=DictCursor) as cur:
            # 1. Fetch Signals
            cur.execute("""
                SELECT content, competitor_id, snapshot_id
                FROM signals
                WHERE cluster_id = %s
            """, (cluster_id,))
            signals = cur.fetchall()
            
            signal_count = len(signals)
            
            # 2. Fetch Latest Trend Data
            cur.execute("""
                SELECT frequency, growth_rate, saturation
                FROM trends
                WHERE cluster_id = %s
                ORDER BY calculated_at DESC
                LIMIT 1
            """, (cluster_id,))
            trend = cur.fetchone()
            
            if trend:
                frequency = trend['frequency'] if trend['frequency'] is not None else 0
                growth_rate = float(trend['growth_rate']) if trend['growth_rate'] is not None else 0.0
                saturation = float(trend['saturation']) if trend['saturation'] is not None else 0.0
            else:
                frequency = 0
                growth_rate = 0.0
                saturation = 0.0

            # 3. Feature Engineering
            positioning_mismatch = 1 if client_positioning == "premium" and saturation > 0.7 else 0

            # 4. Risk Score Calculation
            risk = (
                0.4 * saturation +
                0.2 * (1.0 - growth_rate) +
                0.3 * positioning_mismatch +
                0.1 * (1.0 / (signal_count + 1))
            )
            
            # Clamp result between 0 and 1
            risk = max(0.0, min(1.0, risk))
            risk_score = round(risk, 3)

            # 5. Risk Level Mapping
            if risk_score <= 0.3:
                risk_level = "low"
            elif risk_score <= 0.7:
                risk_level = "medium"
            else:
                risk_level = "high"

            # 6. Risk Explanation
            explanations = []
            if saturation > 0.7:
                explanations.append("High market saturation detected")
            if growth_rate < 0.1:
                explanations.append("Low trend momentum")
            if positioning_mismatch == 1:
                explanations.append("Mismatch with premium positioning")
            if signal_count < 5:
                explanations.append("Low supporting evidence")

            if explanations:
                explanation = ". ".join(explanations)
                if not explanation.endswith("."):
                    explanation += "."
            else:
                explanation = "Low risk scenario"

            # 7. Traceability
            sample_signals = [s['content'] for s in signals[:3] if s['content'] is not None]
            
            # Extract unique competitor IDs (Limit to 5)
            unique_competitors = []
            seen_competitors = set()
            for s in signals:
                cid = s['competitor_id']
                if cid is not None and cid not in seen_competitors:
                    unique_competitors.append(cid)
                    seen_competitors.add(cid)
                    if len(unique_competitors) >= 5:
                        break

            # Return Output Format
            return {
                "risk_score": risk_score,
                "risk_level": risk_level,
                "explanation": explanation,
                "traceability": {
                    "total_signals": signal_count,
                    "sample_signals": sample_signals,
                    "competitor_ids": unique_competitors
                }
            }
            
    finally:
        if conn is not None:
            conn.close()
