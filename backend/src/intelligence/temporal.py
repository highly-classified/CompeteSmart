from sqlalchemy.orm import Session
from sqlalchemy import func
from src.models import Signal, Cluster, Competitor, Trend
from datetime import datetime, timedelta

class TemporalEngine:
    def __init__(self, db: Session):
        self.db = db

    def calculate_trends(self, days_window: int = 7) -> list[dict]:
        now = datetime.utcnow()
        t_current_start = now - timedelta(days=days_window)
        t_prev_start = t_current_start - timedelta(days=days_window)

        clusters = self.db.query(Cluster).all()
        results = []

        for cluster in clusters:
            f_t = self.db.query(Signal).filter(
                Signal.cluster_id == cluster.id,
                Signal.created_at >= t_current_start
            ).count()

            f_t_minus_1 = self.db.query(Signal).filter(
                Signal.cluster_id == cluster.id,
                Signal.created_at >= t_prev_start,
                Signal.created_at < t_current_start
            ).count()
            
            if f_t_minus_1 == 0:
                growth_rate = 1.0 if f_t > 0 else 0.0 
            else:
                growth_rate = (f_t - f_t_minus_1) / f_t_minus_1

            if growth_rate > 0.3:
                trend_status = "emerging"
            elif abs(growth_rate) <= 0.3:
                trend_status = "stable"
            else:
                trend_status = "declining"

            results.append({
                "cluster_id": cluster.id,
                "cluster_label": cluster.label,
                "current_count": f_t,
                "previous_count": f_t_minus_1,
                "growth_rate": round(growth_rate, 4),
                "trend": trend_status
            })
            
        return results

    def calculate_saturation(self) -> list[dict]:
        N = self.db.query(Competitor).count()
        if N == 0:
            return []

        clusters = self.db.query(Cluster).all()
        results = []

        for cluster in clusters:
            c_j = self.db.query(Signal.competitor_id).filter(
                Signal.cluster_id == cluster.id
            ).distinct().count()

            s_j = c_j / N if N > 0 else 0

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

            new_trend = Trend(
                cluster_id=cluster.id,
                frequency=c_j,
                growth_rate=0.0, 
                saturation=s_j
            )
            self.db.add(new_trend)
            
        self.db.commit()
        return results
