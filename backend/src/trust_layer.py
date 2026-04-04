import os
import re
import math
import psycopg2
from psycopg2.extras import DictCursor
from typing import Dict, Any
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

RATING_PATTERN = re.compile(r"rating[:\s]+([0-5](?:\.\d+)?)", re.IGNORECASE)
REVIEW_MARKERS = (
    "review", "reviews", "rated", "rating", "feedback", "experience",
    "top-rated", "customer", "users", "play store"
)
POSITIVE_REVIEW_KEYWORDS = {
    "great", "excellent", "professional", "reliable", "verified", "quality",
    "trusted", "affordable", "top-rated", "good", "best", "securely",
    "resonated", "satisfied", "premium", "clean", "quick"
}
NEGATIVE_REVIEW_KEYWORDS = {
    "poor", "bad", "late", "delay", "complaint", "unreliable", "expensive",
    "issue", "issues", "problem", "problems", "drop-off", "dropoff",
    "booked solid", "solid during weekends", "failed", "failure", "hard"
}


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def _extract_ratings(contents: list[str]) -> list[float]:
    ratings: list[float] = []
    for content in contents:
        if not content:
            continue
        match = RATING_PATTERN.search(content)
        if not match:
            continue
        try:
            rating = float(match.group(1))
        except (TypeError, ValueError):
            continue
        ratings.append(_clamp(rating / 5.0))
    return ratings


def _review_sentiment_score(contents: list[str]) -> tuple[float, int, int, int]:
    positive_hits = 0
    negative_hits = 0
    review_signal_count = 0

    for raw_content in contents:
        content = (raw_content or "").lower()
        if not content:
            continue

        is_review_like = any(marker in content for marker in REVIEW_MARKERS) or bool(RATING_PATTERN.search(content))
        if is_review_like:
            review_signal_count += 1

        positive_hits += sum(1 for keyword in POSITIVE_REVIEW_KEYWORDS if keyword in content)
        negative_hits += sum(1 for keyword in NEGATIVE_REVIEW_KEYWORDS if keyword in content)

    total_hits = positive_hits + negative_hits
    sentiment_score = 0.5 if total_hits == 0 else positive_hits / total_hits
    return sentiment_score, positive_hits, negative_hits, review_signal_count

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
                SELECT s.content, s.competitor_id, s.snapshot_id, s.confidence, c.name AS competitor_name
                FROM signals s
                LEFT JOIN competitors c ON s.competitor_id = c.id
                WHERE s.cluster_id = %s
            """, (cluster_id,))
            signals = cur.fetchall()
            
            signal_count = len(signals)
            signal_contents = [s["content"] for s in signals if s["content"] is not None]
            avg_signal_confidence = (
                sum(float(s["confidence"]) for s in signals if s["confidence"] is not None) / signal_count
                if signal_count > 0 else 0.5
            )
            avg_signal_confidence = _clamp(avg_signal_confidence)
            
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
            momentum_score = _clamp((growth_rate + 1.0) / 2.0)
            evidence_score = _clamp(math.log1p(signal_count) / math.log1p(12)) if signal_count > 0 else 0.0
            ratings = _extract_ratings(signal_contents)
            avg_rating = sum(ratings) / len(ratings) if ratings else 0.0
            sentiment_score, positive_hits, negative_hits, review_signal_count = _review_sentiment_score(signal_contents)
            review_score = (
                (avg_rating * 0.65) + (sentiment_score * 0.35)
                if ratings else sentiment_score
            )
            review_score = _clamp(review_score)
            success_score = _clamp(
                (0.35 * momentum_score) +
                (0.25 * review_score) +
                (0.20 * avg_signal_confidence) +
                (0.20 * evidence_score)
            )
            confidence_score = round(success_score, 3)

            # 4. Risk Score Calculation
            risk = (
                0.28 * saturation +
                0.18 * (1.0 - momentum_score) +
                0.18 * (1.0 - review_score) +
                0.14 * (1.0 - avg_signal_confidence) +
                0.12 * (1.0 - evidence_score) +
                0.10 * positioning_mismatch
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
            if momentum_score < 0.45:
                explanations.append("Low trend momentum")
            if positioning_mismatch == 1:
                explanations.append("Mismatch with premium positioning")
            if signal_count < 5:
                explanations.append("Low supporting evidence")
            if review_score < 0.45:
                explanations.append("Weak review signal quality")
            if avg_signal_confidence < 0.45:
                explanations.append("Low source confidence across supporting signals")

            if explanations:
                explanation = ". ".join(explanations)
                if not explanation.endswith("."):
                    explanation += "."
            else:
                explanation = "Strong evidence, reviews, and momentum support this experiment."

            # 7. Traceability
            sample_signals = [s['content'] for s in signals[:3] if s['content'] is not None]
            
            # Extract unique competitor IDs (Limit to 5)
            unique_competitors = []
            unique_competitor_names = []
            seen_competitors = set()
            for s in signals:
                cid = s['competitor_id']
                if cid is not None and cid not in seen_competitors:
                    unique_competitors.append(cid)
                    if s.get("competitor_name"):
                        unique_competitor_names.append(s["competitor_name"])
                    seen_competitors.add(cid)
                    if len(unique_competitors) >= 5:
                        break

            # Return Output Format
            return {
                "risk_score": risk_score,
                "risk_level": risk_level,
                "confidence_score": confidence_score,
                "success_score": round(success_score, 3),
                "explanation": explanation,
                "traceability": {
                    "total_signals": signal_count,
                    "sample_signals": sample_signals,
                    "competitor_ids": unique_competitors,
                    "competitor_names": unique_competitor_names,
                    "avg_signal_confidence": round(avg_signal_confidence, 3),
                    "review_signal_count": review_signal_count,
                    "avg_rating": round(avg_rating * 5.0, 2) if ratings else None,
                    "positive_review_hits": positive_hits,
                    "negative_review_hits": negative_hits,
                    "review_score": round(review_score, 3),
                    "momentum_score": round(momentum_score, 3),
                    "evidence_score": round(evidence_score, 3),
                }
            }
            
    finally:
        if conn is not None:
            conn.close()
