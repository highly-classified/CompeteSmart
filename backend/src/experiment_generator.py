from src.decision_engine import build_traceability_reasons
from datetime import datetime

def _impact_from_signals(decision_type: str, signals: dict[str, float]) -> int:
    price_sensitivity = float(signals.get("price_sensitivity", 0.0) or 0.0)
    demand_gap = float(signals.get("demand_gap", 0.0) or 0.0)
    competition_density = float(signals.get("competition_density", 0.0) or 0.0)
    review_signal_strength = float(signals.get("review_signal_strength", 0.0) or 0.0)

    if decision_type == "price_drop":
        impact = 10 + (price_sensitivity * 18) + (demand_gap * 6)
    elif decision_type == "differentiation":
        impact = 9 + (competition_density * 12) + (review_signal_strength * 7)
    else:
        impact = 11 + (demand_gap * 16) + (review_signal_strength * 6)

    return max(8, min(int(round(impact)), 35))


def _experiment_template(decision_type: str, category: str, signals: dict[str, float]) -> tuple[str, str, str]:
    price_sensitivity = float(signals.get("price_sensitivity", 0.0) or 0.0)
    discount_pct = max(8, min(int(round(8 + (price_sensitivity * 8))), 15))

    if decision_type == "price_drop":
        return (
            f"Reduce price by {discount_pct}% for first-time users in {category}",
            f"Users in {category} are price-sensitive, so a lower entry price should lift first-time conversion.",
            "Conversion Rate",
        )

    if decision_type == "differentiation":
        return (
            f"A/B test a differentiated premium bundle for {category} with review-proof messaging",
            f"{category} is crowded, so stronger differentiation and proof should improve win rate against competitors.",
            "Booking Conversion Rate",
        )

    return (
        f"Add review proof and faster checkout messaging to the {category} booking flow",
        f"There is demand for {category}, but clearer trust cues and lower friction should increase conversion.",
        "Checkout Conversion Rate",
    )


def generate_experiment_output(
    candidate: dict,
    ml_analysis: dict,
    decision_type: str,
    trust_output: dict,
) -> dict:
    category = candidate.get("cluster_name") or "General Service"
    signals = ml_analysis.get("signals", {})
    traceability_reasons = build_traceability_reasons(
        ml_analysis.get("top_features", []),
        signals,
    )
    experiment, hypothesis, metric = _experiment_template(decision_type, category, signals)
    expected_impact = _impact_from_signals(decision_type, signals)
    risk_score = float(trust_output.get("risk_score", 0.5) or 0.5)
    risk_level = str(trust_output.get("risk_level", "medium")).title()

    return {
        "title": category,
        "category": category,
        "cluster_id": candidate.get("cluster_id"),
        "cluster_name": category,
        "risk": risk_level,
        "risk_score": round(risk_score, 3),
        "confidence": ml_analysis.get("confidence_label", "60%"),
        "confidence_score": ml_analysis.get("confidence_score", 0.6),
        "experiment": experiment,
        "hypothesis": hypothesis,
        "metric": metric,
        "expected_impact": f"+{expected_impact}%",
        "traceability": traceability_reasons,
        "recommended_action": experiment,
        "insight": hypothesis,
        "decision_type": decision_type,
        "ml_score": ml_analysis.get("prediction_score"),
        "ml_signals": signals,
        "feature_importances": ml_analysis.get("feature_importances", {}),
        "trust_and_risk": trust_output,
    }
