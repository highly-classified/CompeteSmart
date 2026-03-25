from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

# --- Clustering Schemas ---
class SignalInput(BaseModel):
    competitor_id: str
    timestamp: datetime
    signal_type: str
    content: str
    
class ClusterResult(BaseModel):
    cluster_id: str
    centroid_vector: List[float]
    members: List[int]
    label: Optional[str] = None

# --- Temporal Schemas ---
class TrendResult(BaseModel):
    cluster_id: str
    cluster_label: str
    current_count: int
    previous_count: int
    growth_rate: float
    trend: str 

class SaturationResult(BaseModel):
    cluster_id: str
    cluster_label: str
    saturation_score: float
    status: str
    competitors_using: int
    total_competitors: int

# --- Advanced Schemas ---
class WhitespaceResult(BaseModel):
    whitespace_theme: str
    supporting_gap_score: float
    candidate_centroid: List[float]

class DriftResult(BaseModel):
    competitor_id: str
    drift_detected: bool
    direction: Optional[str] = None
    magnitude: float
