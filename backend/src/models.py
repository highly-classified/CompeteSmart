from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, Float, ForeignKey
from sqlalchemy.orm import declarative_base, relationship
from pgvector.sqlalchemy import Vector
from datetime import datetime

Base = declarative_base()

class Competitor(Base):
    __tablename__ = "competitors"
    id = Column(String, primary_key=True, index=True)
    name = Column(String, index=True)
    website_url = Column(String)

class ExtractedSignal(Base):
    __tablename__ = "extracted_signals"
    id = Column(Integer, primary_key=True, index=True)
    competitor_id = Column(String, ForeignKey("competitors.id"))
    timestamp = Column(DateTime, default=datetime.utcnow)
    signal_type = Column(String) # e.g., messaging, pricing, feature
    content = Column(Text)
    content_hash = Column(String, unique=True, index=True)
    embedding = Column(Vector(384)) # 384 for all-MiniLM-L6-v2
    cluster_id = Column(String, index=True, nullable=True)

class SignalCluster(Base):
    __tablename__ = "signal_clusters"
    id = Column(String, primary_key=True, index=True)
    label = Column(String)
    centroid_vector = Column(Vector(384))
    created_at = Column(DateTime, default=datetime.utcnow)
