from pydantic import BaseModel
from typing import List, Optional

class WhitespaceResult(BaseModel):
    whitespace_theme: str
    supporting_gap_score: float
    candidate_centroid: List[float]

class DriftResult(BaseModel):
    competitor_id: str
    drift_detected: bool
    direction: Optional[str] = None
    magnitude: float
