import uuid
from sqlalchemy import Column, String, Text, DateTime, Float, ForeignKey, Integer
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
from pgvector.sqlalchemy import Vector
from datetime import datetime

Base = declarative_base()

class Client(Base):
    __tablename__ = "clients"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class Competitor(Base):
    __tablename__ = "competitors"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"))
    name = Column(Text, nullable=False)
    domain = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

class CompetitorUrl(Base):
    __tablename__ = "competitor_urls"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    competitor_id = Column(UUID(as_uuid=True), ForeignKey("competitors.id", ondelete="CASCADE"))
    url = Column(Text, nullable=False)
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
    content_type = Column(Text) # headline, paragraph, CTA, feature
    content = Column(Text, nullable=False)
    content_hash = Column(Text, unique=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Signal(Base):
    __tablename__ = "signals"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    competitor_id = Column(UUID(as_uuid=True), ForeignKey("competitors.id", ondelete="CASCADE"))
    snapshot_id = Column(UUID(as_uuid=True), ForeignKey("snapshots.id", ondelete="CASCADE"), nullable=True)
    content = Column(Text, nullable=False)
    category = Column(Text) # messaging, pricing, CTA, feature
    cluster_id = Column(Text, nullable=True) # assigned after clustering
    created_at = Column(DateTime, default=datetime.utcnow)

class Cluster(Base):
    __tablename__ = "clusters"
    id = Column(Text, primary_key=True) # e.g., "ai_messaging"
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

class Insight(Base):
    __tablename__ = "insights"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cluster_id = Column(Text, ForeignKey("clusters.id"))
    title = Column(Text)
    description = Column(Text)
    confidence = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)

class Risk(Base):
    __tablename__ = "risks"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    insight_id = Column(UUID(as_uuid=True), ForeignKey("insights.id", ondelete="CASCADE"))
    risk_score = Column(Float)
    explanation = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

# Vector DB Representation (Stored in Neon using pgvector plugin)
class VectorEmbedding(Base):
    __tablename__ = "vector_embeddings"
    # The ID maps 1-to-1 with the Document or Signal ID
    id = Column(String, primary_key=True)
    embedding = Column(Vector(384))
    metadata_ = Column(JSONB) # To map metadata as explicitly required
