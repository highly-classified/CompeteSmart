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
 
        # Filter clusters to only those that have signals from the client's competitors
        query = self.db.query(Cluster)
        if client_id:
            query = query.join(Signal, Cluster.id == Signal.cluster_id).join(Competitor, Signal.competitor_id == Competitor.id).filter(Competitor.client_id == client_id)
        
        clusters = query.distinct().all()
        results = []
 
        for cluster in clusters:
            f_t_query = self.db.query(Signal).filter(
                Signal.cluster_id == cluster.id,
                Signal.created_at >= t_current_start
            )
            if client_id:
                f_t_query = f_t_query.join(Competitor, Signal.competitor_id == Competitor.id).filter(Competitor.client_id == client_id)
            f_t = f_t_query.count()
 
            f_t_minus_1_query = self.db.query(Signal).filter(
                Signal.cluster_id == cluster.id,
                Signal.created_at >= t_prev_start,
                Signal.created_at < t_current_start
            )
            if client_id:
                f_t_minus_1_query = f_t_minus_1_query.join(Competitor, Signal.competitor_id == Competitor.id).filter(Competitor.client_id == client_id)
            f_t_minus_1 = f_t_minus_1_query.count()
            
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
 
    def calculate_saturation(self, client_id: int = None) -> list[dict]:
        comp_query = self.db.query(Competitor)
        if client_id:
            comp_query = comp_query.filter(Competitor.client_id == client_id)
        
        N = comp_query.count()
        if N == 0:
            return []
 
        # Filter clusters to those with client signals
        cluster_query = self.db.query(Cluster)
        if client_id:
            cluster_query = cluster_query.join(Signal, Cluster.id == Signal.cluster_id).join(Competitor, Signal.competitor_id == Competitor.id).filter(Competitor.client_id == client_id)
        
        clusters = cluster_query.distinct().all()
        results = []
 
        for cluster in clusters:
            c_j_query = self.db.query(Signal.competitor_id).filter(
                Signal.cluster_id == cluster.id
            )
            if client_id:
                c_j_query = c_j_query.join(Competitor, Signal.competitor_id == Competitor.id).filter(Competitor.client_id == client_id)
            
            c_j = c_j_query.distinct().count()
 
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
