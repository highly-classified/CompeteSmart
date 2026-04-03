import logging
import math

from src.decision_engine import choose_experiment_type
from src.ml_model import MarketStrategyRanker
from datetime import datetime

logger = logging.getLogger(__name__)
ranker = MarketStrategyRanker()


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def _to_momentum_score(growth_rate: float) -> float:
    return _clamp((float(growth_rate or 0.0) + 1.0) / 2.0)


def _to_evidence_strength(evidence_count: int) -> float:
    if evidence_count <= 0:
        return 0.0
    return _clamp(math.log1p(evidence_count) / math.log1p(12))


def _build_ml_features(insight: dict) -> dict[str, float]:
    saturation = _clamp(float(insight.get("saturation", 0.0) or 0.0))
    momentum_score = _to_momentum_score(float(insight.get("trend", 0.0) or 0.0))
    evidence_count = int(insight.get("evidence_count", 0) or 0)
    evidence_strength = _to_evidence_strength(evidence_count)
    avg_signal_confidence = _clamp(float(insight.get("avg_signal_confidence", 0.5) or 0.5))
    review_signal_strength = _clamp(float(insight.get("review_signal_strength", 0.4) or 0.4))
    price_signal_strength = _clamp(float(insight.get("price_signal_strength", 0.25) or 0.25))
    whitespace_personas = insight.get("whitespace_personas", []) or []
    budget_whitespace_bonus = 0.15 if "budget-conscious" in whitespace_personas else 0.0

    price_sensitivity = _clamp(
        (price_signal_strength * 0.55)
        + ((1.0 - saturation) * 0.15)
        + (review_signal_strength * 0.10)
        + (avg_signal_confidence * 0.05)
        + budget_whitespace_bonus
    )
    demand_gap = _clamp(
        (momentum_score * 0.45)
        + ((1.0 - saturation) * 0.30)
        + (review_signal_strength * 0.15)
        + (evidence_strength * 0.10)
    )
    competition_density = saturation

    return {
        "price_sensitivity": round(price_sensitivity, 3),
        "demand_gap": round(demand_gap, 3),
        "competition_density": round(competition_density, 3),
        "review_signal_strength": round(((review_signal_strength * 0.7) + (avg_signal_confidence * 0.3)), 3),
        "evidence_strength": round(evidence_strength, 3),
    }


def generate_ranked_experiment_candidates(insights: list[dict]) -> list[dict]:
    candidates = []

    for insight in insights:
        ml_features = _build_ml_features(insight)
        ml_analysis = ranker.analyze_candidate(ml_features)
        decision_type = choose_experiment_type(ml_analysis["signals"])
        candidates.append({
            **insight,
            "priority_score": ml_analysis["prediction_score"],
            "ml_features": ml_features,
            "ml_analysis": ml_analysis,
            "decision_type": decision_type,
        })

    ranked = sorted(
        candidates,
        key=lambda item: item.get("priority_score", 0.0),
        reverse=True,
    )
    return ranked[:3]


def process_decisions_ml(insights: list[dict]) -> list[dict]:
    """
    Compatibility wrapper for callers expecting ML-ranked candidates.
    """
    ranked_candidates = generate_ranked_experiment_candidates(insights)
    output = []
    for candidate in ranked_candidates:
        ml_analysis = candidate["ml_analysis"]
        output.append({
            "cluster_id": candidate["cluster_id"],
            "cluster_name": candidate["cluster_name"],
            "priority_score": candidate["priority_score"],
            "confidence": ml_analysis["confidence_score"],
            "confidence_label": ml_analysis["confidence_label"],
            "ml_signals": ml_analysis["signals"],
            "decision_type": candidate["decision_type"],
        })
    return output
