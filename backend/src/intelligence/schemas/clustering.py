from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

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
