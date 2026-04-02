import uuid
from sqlalchemy import Column, String, Text, DateTime, Float, ForeignKey, Integer
from sqlalchemy.orm import declarative_base
from sqlalchemy.dialects.postgresql import JSONB
from pgvector.sqlalchemy import Vector
from datetime import datetime

Base = declarative_base()

# ==========================================
# 1. SCRAPING LAYER TABLES (Mapped to Teammate's exact structure)
# ==========================================
class Competitor(Base):
    __tablename__ = "competitors"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(Text, nullable=False)
    domain = Column(Text)
    client_id = Column(Integer, nullable=True) # Mapping: competitors belong to a specific client

class ScrapeState(Base):
    __tablename__ = "scrape_state"
    url = Column(Text, primary_key=True)
    last_scraped_at = Column(DateTime)

class Snapshot(Base):
    __tablename__ = "snapshots"
    id = Column(Integer, primary_key=True, autoincrement=True)
    competitor_id = Column(Integer, ForeignKey("competitors.id", ondelete="CASCADE"))
    url = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

class ExtractedContent(Base):
    __tablename__ = "extracted_content"
    id = Column(Integer, primary_key=True, autoincrement=True)
    snapshot_id = Column(Integer, ForeignKey("snapshots.id", ondelete="CASCADE"))
    content_type = Column(Text) 
    content = Column(Text, nullable=False)
    content_hash = Column(Text, unique=True)
    created_at = Column(DateTime, default=datetime.utcnow)

# ==========================================
# 2. INTELLIGENCE LAYER TABLES (Created by our pipeline)
# ==========================================
class Signal(Base):
    __tablename__ = "signals"
    id = Column(Integer, primary_key=True, autoincrement=True)
    competitor_id = Column(Integer, ForeignKey("competitors.id", ondelete="CASCADE"))
    snapshot_id = Column(Integer, ForeignKey("snapshots.id", ondelete="CASCADE"), nullable=True)
    content = Column(Text, nullable=False)
    category = Column(Text) 
    cluster_id = Column(Text, nullable=True) 
    created_at = Column(DateTime, default=datetime.utcnow)

class Cluster(Base):
    __tablename__ = "clusters"
    id = Column(Text, primary_key=True)
    label = Column(Text)
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

class Trend(Base):
    __tablename__ = "trends"
    id = Column(Integer, primary_key=True, autoincrement=True)
    cluster_id = Column(Text, ForeignKey("clusters.id"))
    frequency = Column(Integer)
    growth_rate = Column(Float)
    saturation = Column(Float)
    calculated_at = Column(DateTime, default=datetime.utcnow)

class VectorEmbedding(Base):
    __tablename__ = "vector_embeddings"
    id = Column(String, primary_key=True)
    embedding = Column(Vector(384))
    metadata_ = Column(JSONB)

class UserProfile(Base):
    __tablename__ = "user_profiles"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    company_name = Column(String, nullable=False)
    website = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
