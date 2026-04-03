import logging
import math

from src.decision_engine import generate_candidates, score_experiment
from src.ml_model import MarketStrategyRanker

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

    return {
        "price_sensitivity": round(price_sensitivity, 3),
        "demand_gap": round(demand_gap, 3),
        "competition_density": round(saturation, 3),
        "review_signal_strength": round(((review_signal_strength * 0.7) + (avg_signal_confidence * 0.3)), 3),
        "evidence_strength": round(evidence_strength, 3),
    }


def _select_top_candidates(candidates: list[dict], limit: int = 3) -> list[dict]:
    ranked = sorted(candidates, key=lambda item: item.get("candidate_score", 0.0), reverse=True)
    selected: list[dict] = []
    used_types: set[str] = set()
    used_clusters: set[str] = set()

    for candidate in ranked:
        if candidate["type"] in used_types:
            continue
        if candidate["cluster_id"] in used_clusters:
            continue
        selected.append(candidate)
        used_types.add(candidate["type"])
        used_clusters.add(candidate["cluster_id"])
        if len(selected) == limit:
            return selected

    for candidate in ranked:
        if len(selected) == limit:
            break
        if candidate["type"] in used_types:
            continue
        if candidate not in selected:
            selected.append(candidate)
            used_types.add(candidate["type"])

    return selected[:limit]


def generate_ranked_experiment_candidates(insights: list[dict]) -> list[dict]:
    all_candidates = []

    for insight in insights:
        ml_features = _build_ml_features(insight)
        ml_analysis = ranker.analyze_candidate(ml_features)
        signals = ml_analysis["signals"]
        base_score = float(ml_analysis["prediction_score"] or 0.0)

        for candidate in generate_candidates(insight.get("cluster_name", "General Service"), signals):
            candidate_score = score_experiment(candidate, signals)
            combined_score = round((candidate_score * 0.65) + (base_score * 0.35), 3)
            all_candidates.append({
                **insight,
                **candidate,
                "priority_score": combined_score,
                "candidate_score": combined_score,
                "ml_features": ml_features,
                "ml_analysis": ml_analysis,
            })

    return _select_top_candidates(all_candidates, limit=3)


def process_decisions_ml(insights: list[dict]) -> list[dict]:
    ranked_candidates = generate_ranked_experiment_candidates(insights)
    output = []
    for candidate in ranked_candidates:
        ml_analysis = candidate["ml_analysis"]
        output.append({
            "cluster_id": candidate["cluster_id"],
            "cluster_name": candidate["cluster_name"],
            "priority_score": candidate["candidate_score"],
            "confidence": ml_analysis["confidence_score"],
            "confidence_label": ml_analysis["confidence_label"],
            "ml_signals": ml_analysis["signals"],
            "decision_type": candidate["type"],
            "variation": candidate["variation"],
        })
    return output
