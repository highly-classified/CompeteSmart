import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
import joblib
import os
import logging

logger = logging.getLogger(__name__)

class MarketStrategyRanker:
    def __init__(self, model_path="market_ranker_model.joblib"):
        self.model_path = model_path
        self.model = None
        self.scaler = StandardScaler()
        self.features = ['momentum', 'saturation', 'risk', 'evidence_count']
        
        # Load model if exists
        if os.path.exists(self.model_path):
            self.load()
        else:
            self._initialize_baseline_model()

    def _initialize_baseline_model(self):
        """Initializes a model with strategic baseline weights if no trained model exists."""
        logger.info("Initializing baseline ML strategy model...")
        # Create synthetic training data based on strategic priorities:
        # High Momentum, Low Saturation, Low Risk, High Evidence = SUCCESS
        n_samples = 200
        np.random.seed(42)
        
        X = pd.DataFrame({
            "momentum": np.random.uniform(-0.5, 1.0, n_samples),
            "saturation": np.random.uniform(0.1, 0.9, n_samples),
            "risk": np.random.uniform(0.1, 0.9, n_samples),
            "evidence_count": np.random.randint(1, 20, n_samples)
        })
        
        # Success Score Formula: 50% Momentum, 20% Saturation inverse, 20% Risk inverse, 10% Evidence
        y = (
            (X["momentum"] * 0.5) + 
            ((1.0 - X["saturation"]) * 0.2) + 
            ((1.0 - X["risk"]) * 0.2) + 
            (np.log1p(X["evidence_count"]) * 0.1)
        )
        
        self.scaler.fit(X)
        self.model = RandomForestRegressor(n_estimators=100, random_state=42)
        self.model.fit(self.scaler.transform(X), y)
        self.save()

    def predict_score(self, features_dict):
        """Predicts a strategic score (0-1) for a given market scenario."""
        if self.model is None:
            return 0.5
            
        # Ensure features are in the right format
        df_input = pd.DataFrame([features_dict])[self.features]
        X_scaled = self.scaler.transform(df_input)
        return float(self.model.predict(X_scaled)[0])

    def rank_experiments(self, experiments_list):
        """
        Takes a list of experiment candidates and returns them sorted by ML score.
        Each experiment must have momentum, saturation, risk, and evidence_count.
        """
        if not experiments_list:
            return []
            
        scored_experiments = []
        for exp in experiments_list:
            feat = {
                "momentum": exp.get("momentum", 0.0),
                "saturation": exp.get("saturation", 0.5),
                "risk": exp.get("risk", 0.5),
                "evidence_count": exp.get("evidence_count", 1)
            }
            score = self.predict_score(feat)
            exp["ml_score"] = score
            scored_experiments.append(exp)
            
        # Sort by ML score descending
        return sorted(scored_experiments, key=lambda x: x["ml_score"], reverse=True)

    def save(self):
        joblib.dump({"model": self.model, "scaler": self.scaler}, self.model_path)
        logger.info(f"Model saved to {self.model_path}")

    def load(self):
        try:
            data = joblib.load(self.model_path)
            self.model = data["model"]
            self.scaler = data["scaler"]
            logger.info("ML Market Ranker model loaded successfully.")
        except Exception as e:
            logger.error(f"Failed to load ML model: {e}")
            self._initialize_baseline_model()
