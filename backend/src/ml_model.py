import logging
import os
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler

try:
    from xgboost import XGBRegressor
except ImportError:  # pragma: no cover - optional dependency
    XGBRegressor = None


logger = logging.getLogger(__name__)


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


class MarketStrategyRanker:
    def __init__(self, model_path: str = "market_ranker_xgb_model.joblib"):
        self.model_path = model_path
        self.model: Any = None
        self.scaler = StandardScaler()
        self.features = [
            "price_sensitivity",
            "demand_gap",
            "competition_density",
            "review_signal_strength",
            "evidence_strength",
        ]
        self.model_family = "xgboost" if XGBRegressor is not None else "random_forest"

        if os.path.exists(self.model_path):
            self.load()
        else:
            self._initialize_baseline_model()

    def _build_estimator(self):
        if XGBRegressor is not None:
            return XGBRegressor(
                objective="reg:squarederror",
                n_estimators=140,
                max_depth=4,
                learning_rate=0.08,
                subsample=0.9,
                colsample_bytree=0.9,
                random_state=42,
            )
        return RandomForestRegressor(n_estimators=140, random_state=42)

    def _initialize_baseline_model(self):
        logger.info("Initializing baseline market strategy model...")
        n_samples = 320
        np.random.seed(42)

        X = pd.DataFrame({
            "price_sensitivity": np.random.uniform(0.1, 1.0, n_samples),
            "demand_gap": np.random.uniform(0.05, 1.0, n_samples),
            "competition_density": np.random.uniform(0.05, 1.0, n_samples),
            "review_signal_strength": np.random.uniform(0.1, 1.0, n_samples),
            "evidence_strength": np.random.uniform(0.05, 1.0, n_samples),
        })

        y = (
            (X["demand_gap"] * 0.34)
            + ((1.0 - X["competition_density"]) * 0.22)
            + (X["review_signal_strength"] * 0.18)
            + (X["evidence_strength"] * 0.16)
            + (X["price_sensitivity"] * 0.10)
        )

        self.scaler.fit(X)
        self.model = self._build_estimator()
        self.model.fit(self.scaler.transform(X), y)
        self.save()

    def _prepare_features(self, features_dict: dict[str, Any]) -> pd.DataFrame:
        prepared = {}
        for feature in self.features:
            value = features_dict.get(feature, 0.0)
            prepared[feature] = _clamp(float(value))
        return pd.DataFrame([prepared])[self.features]

    def predict_score(self, features_dict: dict[str, Any]) -> float:
        if self.model is None:
            return 0.5

        df_input = self._prepare_features(features_dict)
        X_scaled = self.scaler.transform(df_input)
        prediction = float(self.model.predict(X_scaled)[0])
        return _clamp(prediction)

    def _predict_confidence(self, features_dict: dict[str, Any], prediction_score: float) -> tuple[float, str]:
        if self.model is not None and hasattr(self.model, "predict_proba"):
            df_input = self._prepare_features(features_dict)
            X_scaled = self.scaler.transform(df_input)
            probabilities = self.model.predict_proba(X_scaled)[0]
            confidence_pct = int(max(probabilities) * 100)
        else:
            confidence_pct = int(round(60 + (prediction_score * 35)))

        confidence_pct = max(60, min(confidence_pct, 95))
        confidence_score = round(confidence_pct / 100.0, 3)
        return confidence_score, f"{confidence_pct}%"

    def get_feature_importances(self) -> dict[str, float]:
        if self.model is None or not hasattr(self.model, "feature_importances_"):
            uniform_weight = round(1.0 / len(self.features), 4)
            return {feature: uniform_weight for feature in self.features}

        importances = np.array(self.model.feature_importances_, dtype=float)
        total = float(importances.sum()) or 1.0
        normalized = importances / total
        return {
            feature: round(float(weight), 4)
            for feature, weight in zip(self.features, normalized)
        }

    def analyze_candidate(self, features_dict: dict[str, Any]) -> dict[str, Any]:
        prepared = self._prepare_features(features_dict).iloc[0].to_dict()
        prediction_score = self.predict_score(prepared)
        confidence_score, confidence_label = self._predict_confidence(prepared, prediction_score)
        feature_importances = self.get_feature_importances()
        top_features = sorted(
            feature_importances.items(),
            key=lambda item: item[1],
            reverse=True,
        )[:3]

        signals = {
            "price_sensitivity": round(prepared["price_sensitivity"], 3),
            "demand_gap": round(prepared["demand_gap"], 3),
            "competition_density": round(prepared["competition_density"], 3),
            "review_signal_strength": round(prepared["review_signal_strength"], 3),
            "evidence_strength": round(prepared["evidence_strength"], 3),
        }

        return {
            "model_family": self.model_family,
            "prediction_score": round(prediction_score, 3),
            "confidence_score": confidence_score,
            "confidence_label": confidence_label,
            "signals": signals,
            "feature_importances": feature_importances,
            "top_features": top_features,
        }

    def rank_experiments(self, experiments_list: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not experiments_list:
            return []

        ranked: list[dict[str, Any]] = []
        for experiment in experiments_list:
            ml_features = experiment.get("ml_features") or experiment
            analysis = self.analyze_candidate(ml_features)
            enriched = {
                **experiment,
                "ml_score": analysis["prediction_score"],
                "ml_confidence_score": analysis["confidence_score"],
                "ml_confidence_label": analysis["confidence_label"],
                "ml_signals": analysis["signals"],
                "feature_importances": analysis["feature_importances"],
                "top_features": analysis["top_features"],
                "ml_analysis": analysis,
            }
            ranked.append(enriched)

        return sorted(ranked, key=lambda item: item["ml_score"], reverse=True)

    def save(self):
        joblib.dump(
            {
                "model": self.model,
                "scaler": self.scaler,
                "features": self.features,
                "model_family": self.model_family,
            },
            self.model_path,
        )
        logger.info("Model saved to %s", self.model_path)

    def load(self):
        try:
            data = joblib.load(self.model_path)
            self.model = data["model"]
            self.scaler = data["scaler"]
            loaded_features = data.get("features")
            if loaded_features != self.features:
                raise ValueError("Stored feature schema does not match current model schema.")
            self.model_family = data.get("model_family", self.model_family)
            logger.info("ML market ranker loaded successfully.")
        except Exception as exc:
            logger.error("Failed to load ML model: %s", exc)
            self._initialize_baseline_model()
