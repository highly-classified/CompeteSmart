from sqlalchemy.orm import Session
from sqlalchemy import func
from src.models import Signal, Cluster, Competitor, Trend
from datetime import datetime, timedelta

class TemporalEngine:
    def __init__(self, db: Session):
        self.db = db

    def calculate_trends(self, client_id: int = None, days_window: int = 7) -> list[dict]:
        now = datetime.utcnow()
        t_current_start = now - timedelta(days=days_window)
        t_prev_start = t_current_start - timedelta(days=days_window)

        # 1. Fetch cluster labels first (needed for display)
        clusters_map = {c.id: c.clean_label for c in self.db.query(Cluster.id, Cluster.clean_label).filter(Cluster.clean_label != "").all()}
        
        # 2. Aggregate current counts via GroupBy
        current_counts_query = self.db.query(Signal.cluster_id, func.count(Signal.id)).filter(Signal.created_at >= t_current_start)
        if client_id:
            current_counts_query = current_counts_query.join(Competitor, Signal.competitor_id == Competitor.id).filter(Competitor.client_id == client_id)
        current_counts = dict(current_counts_query.group_by(Signal.cluster_id).all())

        # 3. Aggregate previous counts via GroupBy
        prev_counts_query = self.db.query(Signal.cluster_id, func.count(Signal.id)).filter(Signal.created_at >= t_prev_start, Signal.created_at < t_current_start)
        if client_id:
            prev_counts_query = prev_counts_query.join(Competitor, Signal.competitor_id == Competitor.id).filter(Competitor.client_id == client_id)
        prev_counts = dict(prev_counts_query.group_by(Signal.cluster_id).all())

        results = []
        for cid, label in clusters_map.items():
            f_t = current_counts.get(cid, 0)
            f_prev = prev_counts.get(cid, 0)
            
            growth_rate = (f_t - f_prev) / f_prev if f_prev > 0 else (1.0 if f_t > 0 else 0.0)
            trend_status = "emerging" if growth_rate > 0.3 else ("declining" if growth_rate < -0.3 else "stable")

            results.append({
                "cluster_id": cid,
                "cluster_label": label,
                "current_count": f_t,
                "previous_count": f_prev,
                "growth_rate": round(float(growth_rate), 4),
                "trend": trend_status
            })
            
        return results
 
    def calculate_saturation(self, client_id: int = None) -> list[dict]:
        # 1. Get N (Total tracked competitors)
        comp_query = self.db.query(Competitor)
        if client_id:
            comp_query = comp_query.filter(Competitor.client_id == client_id)
        N = comp_query.count()
        if N == 0: return []

        # 2. Fetch cluster labels
        clusters_map = {c.id: c.clean_label for c in self.db.query(Cluster.id, Cluster.clean_label).filter(Cluster.clean_label != "").all()}

        # 3. Aggregate Competitor counts per cluster using GroupBy
        # In SQL: SELECT cluster_id, COUNT(DISTINCT competitor_id) FROM signals GROUP BY cluster_id
        sat_query = self.db.query(Signal.cluster_id, func.count(Signal.competitor_id.distinct()))
        if client_id:
            sat_query = sat_query.join(Competitor, Signal.competitor_id == Competitor.id).filter(Competitor.client_id == client_id)
        
        sat_counts = dict(sat_query.group_by(Signal.cluster_id).all())

        results = []
        for cid, label in clusters_map.items():
            c_j = sat_counts.get(cid, 0)
            s_j = c_j / N if N > 0 else 0
            
            results.append({
                "cluster_id": cid,
                "cluster_label": label,
                "saturation_score": round(float(s_j), 4),
                "status": "highly_saturated" if s_j > 0.7 else ("moderate" if s_j > 0.4 else "low"),
                "competitors_using": c_j,
                "total_competitors": N
            })
            
        return results

