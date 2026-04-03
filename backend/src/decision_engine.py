from typing import Iterable
import statistics


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def generate_candidates(category: str, signals: dict[str, float]) -> list[dict]:
    price_sensitivity = float(signals.get("price_sensitivity", 0.0) or 0.0)
    demand_gap = float(signals.get("demand_gap", 0.0) or 0.0)
    competition_density = float(signals.get("competition_density", 0.0) or 0.0)

    return [
        {
            "type": "price_drop",
            "variation": f"{max(8, min(int(round(8 + price_sensitivity * 7)), 14))}% off first booking",
            "metric": "Conversion Rate",
        },
        {
            "type": "discount_offer",
            "variation": f"Rs {max(99, min(int(round(99 + demand_gap * 220)), 299))} off first order",
            "metric": "New User Conversion",
        },
        {
            "type": "bundle_offer",
            "variation": "core service + add-on bundle",
            "metric": "Average Order Value",
        },
        {
            "type": "premium_positioning",
            "variation": "premium guarantee + review proof",
            "metric": "Booking Win Rate",
        },
        {
            "type": "urgency_campaign",
            "variation": "48-hour limited-time campaign",
            "metric": "Checkout Conversion Rate",
        },
        {
            "type": "review_proof",
            "variation": "rating-led landing page messaging",
            "metric": "Landing Page Conversion",
        },
    ]


def score_experiment(experiment: dict, signals: dict[str, float]) -> float:
    price_sensitivity = float(signals.get("price_sensitivity", 0.0) or 0.0)
    demand_gap = float(signals.get("demand_gap", 0.0) or 0.0)
    competition_density = float(signals.get("competition_density", 0.0) or 0.0)
    review_signal_strength = float(signals.get("review_signal_strength", 0.0) or 0.0)
    evidence_strength = float(signals.get("evidence_strength", 0.0) or 0.0)

    experiment_type = experiment["type"]
    score = 0.0

    if experiment_type == "price_drop":
        score += price_sensitivity * 0.50
        score += demand_gap * 0.18
        score += review_signal_strength * 0.08
    elif experiment_type == "discount_offer":
        score += demand_gap * 0.30
        score += price_sensitivity * 0.28
        score += evidence_strength * 0.10
    elif experiment_type == "bundle_offer":
        score += (1 - competition_density) * 0.40
        score += demand_gap * 0.22
        score += review_signal_strength * 0.08
    elif experiment_type == "premium_positioning":
        score += review_signal_strength * 0.34
        score += (1 - price_sensitivity) * 0.24
        score += (1 - competition_density) * 0.16
    elif experiment_type == "urgency_campaign":
        score += review_signal_strength * 0.30
        score += demand_gap * 0.24
        score += evidence_strength * 0.12
    elif experiment_type == "review_proof":
        score += review_signal_strength * 0.38
        score += demand_gap * 0.20
        score += competition_density * 0.12

    score += evidence_strength * 0.10
    return round(_clamp(score), 3)


def calculate_confidence(score: float, signals: dict[str, float], top_features: Iterable[tuple[str, float]]) -> tuple[int, float]:
    review_signal_strength = float(signals.get("review_signal_strength", 0.0) or 0.0)
    values = [
        float(signals.get("price_sensitivity", 0.0) or 0.0),
        float(signals.get("demand_gap", 0.0) or 0.0),
        float(signals.get("competition_density", 0.0) or 0.0),
        review_signal_strength,
        float(signals.get("evidence_strength", 0.0) or 0.0),
    ]
    signal_consistency = 1.0 - min(statistics.pstdev(values), 0.35) / 0.35
    feature_strength = sum(float(weight) for _, weight in list(top_features)[:3])
    confidence = (score * 100) + (review_signal_strength * 10) + (feature_strength * 12) + (signal_consistency * 6)
    confidence_pct = int(max(65, min(round(confidence), 92)))
    return confidence_pct, round(confidence_pct / 100.0, 3)


def calculate_impact(experiment: dict, signals: dict[str, float]) -> str:
    price_sensitivity = float(signals.get("price_sensitivity", 0.0) or 0.0)
    demand_gap = float(signals.get("demand_gap", 0.0) or 0.0)
    competition_density = float(signals.get("competition_density", 0.0) or 0.0)
    review_signal_strength = float(signals.get("review_signal_strength", 0.0) or 0.0)
    evidence_strength = float(signals.get("evidence_strength", 0.0) or 0.0)
    candidate_score = float(experiment.get("candidate_score", 0.0) or 0.0)

    experiment_type = experiment["type"]
    if experiment_type == "price_drop":
        impact = (
            price_sensitivity * 19
            + demand_gap * 11
            + (1 - competition_density) * 6
            + candidate_score * 8
        )
    elif experiment_type == "discount_offer":
        impact = (
            demand_gap * 18
            + price_sensitivity * 12
            + evidence_strength * 7
            + candidate_score * 6
        )
    elif experiment_type == "bundle_offer":
        impact = (
            (1 - competition_density) * 16
            + review_signal_strength * 10
            + evidence_strength * 8
            + candidate_score * 7
        )
    elif experiment_type == "premium_positioning":
        impact = (
            review_signal_strength * 17
            + (1 - price_sensitivity) * 12
            + (1 - competition_density) * 8
            + candidate_score * 6
        )
    elif experiment_type == "urgency_campaign":
        impact = (
            demand_gap * 14
            + review_signal_strength * 11
            + evidence_strength * 7
            + candidate_score * 7
        )
    else:
        impact = (
            review_signal_strength * 15
            + demand_gap * 10
            + competition_density * 6
            + candidate_score * 7
        )

    return f"+{int(max(10, min(round(impact), 34)))}%"


def choose_experiment_type(signals: dict[str, float]) -> str:
    candidates = generate_candidates("General Service", signals)
    scored = sorted(
        candidates,
        key=lambda candidate: score_experiment(candidate, signals),
        reverse=True,
    )
    return scored[0]["type"] if scored else "price_drop"


def feature_reason(feature_name: str, signal_value: float) -> str:
    if feature_name == "price_sensitivity":
        if signal_value > 0.7:
            return "High price sensitivity detected"
        if signal_value > 0.5:
            return "Moderate price sensitivity detected"
        return "Pricing flexibility is limited"

    if feature_name == "demand_gap":
        if signal_value > 0.6:
            return "Significant unmet demand"
        if signal_value > 0.4:
            return "Demand gap observed"
        return "Demand is present but still forming"

    if feature_name == "competition_density":
        if signal_value < 0.3:
            return "Low competition pressure"
        if signal_value < 0.55:
            return "Moderate competition pressure"
        return "Competition pressure is high"

    if feature_name == "review_signal_strength":
        if signal_value > 0.65:
            return "Strong review trust signals"
        if signal_value > 0.4:
            return "Review sentiment supports conversion"
        return "Review signals are mixed"

    if feature_name == "evidence_strength":
        if signal_value > 0.65:
            return "Broad evidence coverage across signals"
        if signal_value > 0.4:
            return "Evidence volume is healthy"
        return "Evidence base is still limited"

    return "Model highlighted this signal"


def build_traceability_reasons(
    top_features: Iterable[tuple[str, float]],
    signals: dict[str, float],
) -> list[str]:
    reasons: list[str] = []
    seen = set()
    for feature_name, _importance in top_features:
        reason = feature_reason(feature_name, float(signals.get(feature_name, 0.0) or 0.0))
        if reason not in seen:
            reasons.append(reason)
            seen.add(reason)

    price_sensitivity = float(signals.get("price_sensitivity", 0.0) or 0.0)
    demand_gap = float(signals.get("demand_gap", 0.0) or 0.0)
    competition_density = float(signals.get("competition_density", 0.0) or 0.0)
    review_signal_strength = float(signals.get("review_signal_strength", 0.0) or 0.0)

    if price_sensitivity > 0.7 and "High price sensitivity detected" not in seen:
        reasons.append("High price sensitivity detected")
    if demand_gap > 0.6 and "Significant unmet demand" not in seen:
        reasons.append("Significant unmet demand")
    if competition_density < 0.3 and "Low competition pressure" not in seen:
        reasons.append("Low competition pressure")
    if review_signal_strength > 0.65 and "Strong review trust signals" not in seen:
        reasons.append("Strong review trust signals")

    return reasons[:3]


def build_experiment_traceability(
    experiment: dict,
    top_features: Iterable[tuple[str, float]],
    signals: dict[str, float],
) -> list[str]:
    experiment_type = experiment["type"]
    candidate_score = float(experiment.get("candidate_score", 0.0) or 0.0)
    reasons: list[str] = []
    source_competitors = experiment.get("source_competitors") or []
    source_signal_examples = experiment.get("source_signal_examples") or []

    if source_competitors:
        lead_competitor = source_competitors[0]
        example_signal = next(
            (entry.get("signal") for entry in source_signal_examples if entry.get("competitor") == lead_competitor and entry.get("signal")),
            None,
        )
        if example_signal:
            snippet = str(example_signal).strip().replace("\n", " ")
            snippet = snippet[:88].rstrip(" .,;:")
            reasons.append(f"Derived from {lead_competitor} signal: {snippet}")
        else:
            reasons.append(f"Derived from recurring {lead_competitor} competitor signals")

    if experiment_type == "price_drop":
        reasons.append(f"Price-led intervention ranks highest for this segment (score {candidate_score:.2f})")
    elif experiment_type == "discount_offer":
        reasons.append(f"Intro offer outperforms other acquisition levers for this category (score {candidate_score:.2f})")
    elif experiment_type == "bundle_offer":
        reasons.append(f"Bundle economics look stronger than pure discounting for this category (score {candidate_score:.2f})")
    elif experiment_type == "premium_positioning":
        reasons.append(f"Trust and premium framing outperform discount-heavy approaches here (score {candidate_score:.2f})")
    elif experiment_type == "urgency_campaign":
        reasons.append(f"Urgency-based messaging has stronger timing leverage for this audience (score {candidate_score:.2f})")
    else:
        reasons.append(f"Review-proof messaging outperforms generic copy for this audience (score {candidate_score:.2f})")

    for reason in build_traceability_reasons(top_features, signals):
        if reason not in reasons:
            reasons.append(reason)

    return reasons[:3]
