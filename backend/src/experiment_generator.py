from src.decision_engine import (
    build_experiment_traceability,
    calculate_confidence,
    calculate_impact,
)


def _experiment_copy(experiment_type: str, category: str, variation: str) -> tuple[str, str, str]:
    if experiment_type == "price_drop":
        return (
            f"A/B test {variation} for first-time {category} users against the current list price",
            f"New {category} shoppers appear price-sensitive, so lowering the first purchase threshold should improve conversion.",
            "Conversion Rate",
        )

    if experiment_type == "discount_offer":
        return (
            f"Offer {variation} on the first {category} booking and test it against the no-offer control",
            f"There is measurable demand in {category}, but a sharper introductory offer could unlock more first-time purchases.",
            "New User Conversion",
        )

    if experiment_type == "bundle_offer":
        return (
            f"Package the core {category} service with a relevant add-on and test bundle adoption versus standalone purchase",
            f"Lower competition pressure creates room to raise perceived value with a stronger {category} bundle rather than another discount.",
            "Average Order Value",
        )

    if experiment_type == "premium_positioning":
        return (
            f"Position {category} as a premium, guaranteed experience with {variation} and compare against the standard promise",
            f"Review strength suggests customers may respond to trust and quality framing more than additional discounting in {category}.",
            "Booking Win Rate",
        )

    if experiment_type == "urgency_campaign":
        return (
            f"Run a {variation} for {category} and compare urgency-led creative against evergreen messaging",
            f"Demand exists in {category}, and a stronger urgency trigger may convert more users before they postpone purchase.",
            "Checkout Conversion Rate",
        )

    return (
        f"Lead the {category} flow with {variation} and compare it with the current generic messaging",
        f"Trust and demand signals suggest stronger proof could remove hesitation in the {category} purchase journey.",
        "Landing Page Conversion",
    )


def generate_experiment_output(
    candidate: dict,
    ml_analysis: dict,
    trust_output: dict,
) -> dict:
    category = candidate.get("cluster_name") or "General Service"
    signals = ml_analysis.get("signals", {})
    top_features = ml_analysis.get("top_features", [])
    experiment_type = candidate["type"]
    variation = candidate["variation"]

    experiment, hypothesis, default_metric = _experiment_copy(experiment_type, category, variation)
    confidence_pct, confidence_score = calculate_confidence(
        float(candidate.get("candidate_score", ml_analysis.get("prediction_score", 0.6)) or 0.6),
        signals,
        top_features,
    )
    expected_impact = calculate_impact(candidate, signals)
    traceability_reasons = build_experiment_traceability(candidate, top_features, signals)
    risk_score = float(trust_output.get("risk_score", 0.5) or 0.5)
    risk_level = str(trust_output.get("risk_level", "medium")).title()

    return {
        "title": category,
        "category": category,
        "cluster_id": candidate.get("cluster_id"),
        "cluster_name": category,
        "risk": risk_level,
        "risk_score": round(risk_score, 3),
        "confidence": f"{confidence_pct}%",
        "confidence_score": confidence_score,
        "experiment": experiment,
        "hypothesis": hypothesis,
        "metric": candidate.get("metric") or default_metric,
        "expected_impact": expected_impact,
        "traceability": {
            "reasons": traceability_reasons,
        },
        "recommended_action": experiment,
        "insight": hypothesis,
        "decision_type": experiment_type,
        "variation": variation,
        "candidate_score": round(float(candidate.get("candidate_score", 0.0) or 0.0), 3),
        "ml_score": ml_analysis.get("prediction_score"),
        "ml_signals": signals,
        "feature_importances": ml_analysis.get("feature_importances", {}),
        "trust_and_risk": trust_output,
    }
