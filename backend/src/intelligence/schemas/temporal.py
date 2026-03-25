from pydantic import BaseModel

class TrendResult(BaseModel):
    cluster_id: str
    cluster_label: str
    current_count: int
    previous_count: int
    growth_rate: float
    trend: str # emerging, stable, declining

class SaturationResult(BaseModel):
    cluster_id: str
    cluster_label: str
    saturation_score: float
    status: str
    competitors_using: int
    total_competitors: int
