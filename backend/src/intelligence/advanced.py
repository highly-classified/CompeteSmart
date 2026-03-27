from sqlalchemy.orm import Session
from src.models import Signal, Cluster, VectorEmbedding
from datetime import datetime, timedelta

class AdvancedIntelligenceEngine:
    def __init__(self, db: Session):
        self.db = db

    def detect_whitespace(self, bandwidth: float = 0.5, num_candidates: int = 5) -> list[dict]:
        import numpy as np
        from sklearn.neighbors import KernelDensity
        
        clusters = self.db.query(Cluster).all()
        if not clusters or len(clusters) < 5:
            return []

        centroids = []
        for c in clusters:
            signals = self.db.query(Signal).filter(Signal.cluster_id == c.id).all()
            if signals:
                sig_ids = [str(s.id) for s in signals]
                vecs = self.db.query(VectorEmbedding).filter(VectorEmbedding.id.in_(sig_ids)).all()
                if vecs:
                    arr = np.array([v.embedding for v in vecs])
                    centroids.append(np.mean(arr, axis=0))

        if len(centroids) < 5:
            return []

        embeddings = np.array(centroids)

        kde = KernelDensity(kernel='gaussian', bandwidth=bandwidth).fit(embeddings)
        noise = np.random.normal(0, 0.2, (len(embeddings) * 5, embeddings.shape[1]))
        base_points = np.repeat(embeddings, 5, axis=0)
        candidate_points = base_points + noise

        log_density = kde.score_samples(candidate_points)
        lowest_density_indices = np.argsort(log_density)[:num_candidates]

        results = []
        for idx in lowest_density_indices:
            candidate_vector = candidate_points[idx]
            gap_score = float(-log_density[idx])
            
            results.append({
                "whitespace_theme": "Needs LLM Labeling (Semantic Gap Detected)",
                "supporting_gap_score": round(gap_score, 4),
                "candidate_centroid": candidate_vector.tolist()
            })

        return results

    def detect_persona_drift(self, competitor_id: str, days_window: int = 30) -> dict:
        import numpy as np
        now = datetime.utcnow()
        t_current_start = now - timedelta(days=days_window)
        t_prev_start = t_current_start - timedelta(days=days_window)
        
        def get_mean_vector(t_start, t_end):
            signals = self.db.query(Signal).filter(
                Signal.competitor_id == competitor_id,
                Signal.created_at >= t_start,
                Signal.created_at < t_end
            ).all()
            if not signals: return None
            sig_ids = [str(s.id) for s in signals]
            vecs = self.db.query(VectorEmbedding).filter(VectorEmbedding.id.in_(sig_ids)).all()
            if not vecs: return None
            return np.mean([v.embedding for v in vecs], axis=0)

        p_t = get_mean_vector(t_current_start, now)
        p_t_minus_1 = get_mean_vector(t_prev_start, t_current_start)

        if p_t is None or p_t_minus_1 is None:
            return {
                "competitor_id": competitor_id,
                "drift_detected": False,
                "magnitude": 0.0,
                "direction": "insufficient_data"
            }

        magnitude = np.linalg.norm(p_t - p_t_minus_1)
        drift_detected = bool(magnitude > 0.4) 

        return {
            "competitor_id": str(competitor_id),
            "drift_detected": drift_detected,
            "magnitude": round(float(magnitude), 4),
            "direction": "semantic_shift"
        }
