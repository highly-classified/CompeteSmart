from typing import Iterable
from datetime import datetime

def choose_experiment_type(signals: dict[str, float]) -> str:
    price_sensitivity = float(signals.get("price_sensitivity", 0.0) or 0.0)
    demand_gap = float(signals.get("demand_gap", 0.0) or 0.0)
    competition_density = float(signals.get("competition_density", 0.0) or 0.0)
    review_signal_strength = float(signals.get("review_signal_strength", 0.0) or 0.0)

    if price_sensitivity > 0.75:
        return "price_drop"
    if demand_gap > 0.55 and review_signal_strength >= 0.4:
        return "conversion_boost"
    if competition_density > 0.5:
        return "differentiation"
    return "conversion_boost"


def feature_reason(feature_name: str, signal_value: float) -> str:
    if feature_name == "price_sensitivity":
        if signal_value > 0.75:
            return "High price sensitivity influence"
        if signal_value > 0.5:
            return "Moderate price sensitivity detected"
        return "Pricing is a secondary lever"

    if feature_name == "demand_gap":
        if signal_value > 0.6:
            return "Demand gap detected"
        if signal_value > 0.4:
            return "Emerging unmet demand"
        return "Demand signal is still forming"

    if feature_name == "competition_density":
        if signal_value > 0.65:
            return "Competition pressure high"
        if signal_value > 0.4:
            return "Moderate competition pressure"
        return "Competition density remains manageable"

    if feature_name == "review_signal_strength":
        if signal_value > 0.65:
            return "Review quality supports stronger conversion intent"
        if signal_value > 0.4:
            return "Review signals are directionally positive"
        return "Review signals are mixed"

    if feature_name == "evidence_strength":
        if signal_value > 0.65:
            return "Broad evidence coverage across signals"
        if signal_value > 0.4:
            return "Evidence volume is adequate"
        return "Evidence base is still thin"

    return "Model highlighted this signal"


def build_traceability_reasons(
    top_features: Iterable[tuple[str, float]],
    signals: dict[str, float],
) -> list[str]:
    reasons: list[str] = []
    for feature_name, _importance in top_features:
        reasons.append(feature_reason(feature_name, float(signals.get(feature_name, 0.0) or 0.0)))
    return reasons[:3]
