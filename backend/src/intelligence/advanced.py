import numpy as np
from sqlalchemy.orm import Session
from src.models import ExtractedSignal, SignalCluster
from sklearn.neighbors import KernelDensity
from datetime import datetime, timedelta

class AdvancedIntelligenceEngine:
    def __init__(self, db: Session):
        self.db = db

    def detect_whitespace(self, bandwidth: float = 0.5, num_candidates: int = 5) -> list[dict]:
        """
        Identifies regions in the semantic embedding space with low density (whitespace).
        """
        clusters = self.db.query(SignalCluster).all()
        if not clusters or len(clusters) < 5:
            return []

        embeddings = np.array([c.centroid_vector for c in clusters])

        # Step 1: Kernel Density Estimation
        kde = KernelDensity(kernel='gaussian', bandwidth=bandwidth).fit(embeddings)

        # Step 2: Candidate Generation
        # In high dimensions (384), uniform sampling is ineffective (curse of dimensionality).
        # We generate candidates near the manifold by perturbing existing clusters
        # and checking if the new location falls into a low-density "gap".
        noise = np.random.normal(0, 0.2, (len(embeddings) * 5, embeddings.shape[1]))
        base_points = np.repeat(embeddings, 5, axis=0)
        candidate_points = base_points + noise

        # Step 3: Density Evaluation
        log_density = kde.score_samples(candidate_points)
        
        # Get points with lowest density (highest whitespace potential)
        lowest_density_indices = np.argsort(log_density)[:num_candidates]

        results = []
        for idx in lowest_density_indices:
            candidate_vector = candidate_points[idx]
            gap_score = float(-log_density[idx]) # Higher negative log density = bigger gap
            
            # Label generation would normally require an LLM call to decode the vector.
            results.append({
                "whitespace_theme": "Needs LLM Labeling (Semantic Gap Detected)",
                "supporting_gap_score": round(gap_score, 4),
                "candidate_centroid": candidate_vector.tolist()
            })

        return results

    def detect_persona_drift(self, competitor_id: str, days_window: int = 30) -> dict:
        """
        Detects if a competitor has shifted their messaging focus over time by tracking
        their feature vector drift in the semantic space.
        """
        now = datetime.utcnow()
        t_current_start = now - timedelta(days=days_window)
        t_prev_start = t_current_start - timedelta(days=days_window)
        
        curr_signals = self.db.query(ExtractedSignal).filter(
            ExtractedSignal.competitor_id == competitor_id,
            ExtractedSignal.timestamp >= t_current_start
        ).all()

        prev_signals = self.db.query(ExtractedSignal).filter(
            ExtractedSignal.competitor_id == competitor_id,
            ExtractedSignal.timestamp >= t_prev_start,
            ExtractedSignal.timestamp < t_current_start
        ).all()

        if not curr_signals or not prev_signals:
            return {
                "competitor_id": competitor_id,
                "drift_detected": False,
                "magnitude": 0.0,
                "direction": "insufficient_data"
            }

        # Average their semantic embeddings over time to find their "Persona Centroid"
        p_t = np.mean([s.embedding for s in curr_signals], axis=0)
        p_t_minus_1 = np.mean([s.embedding for s in prev_signals], axis=0)

        # Euclidean shift magnitude
        magnitude = np.linalg.norm(p_t - p_t_minus_1)

        # Threshold to constitute a genuine drift (tunable)
        drift_detected = bool(magnitude > 0.4) 

        return {
            "competitor_id": competitor_id,
            "drift_detected": drift_detected,
            "magnitude": round(float(magnitude), 4),
            "direction": "semantic_shift"
        }
