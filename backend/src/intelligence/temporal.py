from sqlalchemy.orm import Session
from sqlalchemy import func
from src.models import ExtractedSignal, SignalCluster, Competitor
from datetime import datetime, timedelta

class TemporalEngine:
    def __init__(self, db: Session):
        self.db = db

    def calculate_trends(self, days_window: int = 7) -> list[dict]:
        """
        Calculates the growth rate of signals per cluster over a 2-period window.
        """
        now = datetime.utcnow()
        t_current_start = now - timedelta(days=days_window)
        t_prev_start = t_current_start - timedelta(days=days_window)

        clusters = self.db.query(SignalCluster).all()
        results = []

        for cluster in clusters:
            f_t = self.db.query(ExtractedSignal).filter(
                ExtractedSignal.cluster_id == cluster.id,
                ExtractedSignal.timestamp >= t_current_start
            ).count()

            f_t_minus_1 = self.db.query(ExtractedSignal).filter(
                ExtractedSignal.cluster_id == cluster.id,
                ExtractedSignal.timestamp >= t_prev_start,
                ExtractedSignal.timestamp < t_current_start
            ).count()
            
            # Growth Rate
            if f_t_minus_1 == 0:
                growth_rate = 1.0 if f_t > 0 else 0.0 
            else:
                growth_rate = (f_t - f_t_minus_1) / f_t_minus_1

            # Trend Classification
            if growth_rate > 0.3:
                trend = "emerging"
            elif abs(growth_rate) <= 0.3:
                trend = "stable"
            else:
                trend = "declining"

            results.append({
                "cluster_id": cluster.id,
                "cluster_label": cluster.label,
                "current_count": f_t,
                "previous_count": f_t_minus_1,
                "growth_rate": round(growth_rate, 4),
                "trend": trend
            })
            
        return results

    def calculate_saturation(self) -> list[dict]:
        """
        Calculates how widely adopted a cluster's messaging is across competitors.
        S_j = |C_j| / N
        """
        N = self.db.query(Competitor).count()
        if N == 0:
            return [] # No competitors defined yet

        clusters = self.db.query(SignalCluster).all()
        results = []

        for cluster in clusters:
            c_j = self.db.query(ExtractedSignal.competitor_id).filter(
                ExtractedSignal.cluster_id == cluster.id
            ).distinct().count()

            s_j = c_j / N

            # Thresholds
            if s_j > 0.7:
                status = "highly_saturated"
            elif s_j > 0.4:
                status = "moderate"
            else:
                status = "low"

            results.append({
                "cluster_id": cluster.id,
                "cluster_label": cluster.label,
                "saturation_score": round(s_j, 4),
                "status": status,
                "competitors_using": c_j,
                "total_competitors": N
            })

        return results
