import uuid
from sqlalchemy import Column, String, Text, DateTime, Float, ForeignKey, Integer
from sqlalchemy.orm import declarative_base
from sqlalchemy.dialects.postgresql import UUID, JSONB
from pgvector.sqlalchemy import Vector
from datetime import datetime

Base = declarative_base()

# ==========================================
# 1. SCRAPING LAYER TABLES (Mapped to Teammate's exact structure)
# ==========================================
class Competitor(Base):
    __tablename__ = "competitors"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(Text, nullable=False)
    domain = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

class ScrapeState(Base):
    __tablename__ = "scrape_state"
    url = Column(Text, primary_key=True)
    last_scraped_at = Column(DateTime)

class Snapshot(Base):
    __tablename__ = "snapshots"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    competitor_id = Column(UUID(as_uuid=True), ForeignKey("competitors.id", ondelete="CASCADE"))
    url = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

class ExtractedContent(Base):
    __tablename__ = "extracted_content"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    snapshot_id = Column(UUID(as_uuid=True), ForeignKey("snapshots.id", ondelete="CASCADE"))
    content_type = Column(Text) 
    content = Column(Text, nullable=False)
    content_hash = Column(Text, unique=True)
    created_at = Column(DateTime, default=datetime.utcnow)

# ==========================================
# 2. INTELLIGENCE LAYER TABLES (Created by our pipeline)
# ==========================================
class Signal(Base):
    __tablename__ = "signals"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    competitor_id = Column(UUID(as_uuid=True), ForeignKey("competitors.id", ondelete="CASCADE"))
    snapshot_id = Column(UUID(as_uuid=True), ForeignKey("snapshots.id", ondelete="CASCADE"), nullable=True)
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
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
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
