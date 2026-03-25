import hashlib
import numpy as np
import hdbscan
from sentence_transformers import SentenceTransformer
from sqlalchemy.orm import Session
from src.models import Signal, Cluster, VectorEmbedding
import uuid
from datetime import datetime
from sqlalchemy import cast, String

model = SentenceTransformer('all-MiniLM-L6-v2')

class ClusteringEngine:
    def __init__(self, db: Session):
        self.db = db

    def process_new_signals(self, raw_signals: list[dict]):
        processed = []
        for signal in raw_signals:
            content = signal["content"].lower().strip()
            
            # Generate Embedding
            embedding = model.encode(content).tolist()
            
            # Store cleanly in strict relational table
            new_signal = Signal(
                competitor_id=signal["competitor_id"],
                category=signal["signal_type"],
                content=content
            )
            self.db.add(new_signal)
            self.db.flush() # Force ID generation
            
            # Store embeddings explicitly in the Vector DB structural table
            vec = VectorEmbedding(
                id=str(new_signal.id),
                embedding=embedding,
                metadata_={
                    "competitor_id": str(signal["competitor_id"]),
                    "category": signal["signal_type"],
                    "content": content,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
            self.db.add(vec)
            processed.append(new_signal)
            
    def sync_missing_embeddings(self):
        """
        Safety Net: If the scraping team writes directly to the Neon PostgreSQL 
        `signals` table, this function finds signals without embeddings, 
        generates them, and stores them in the Vector DB automatically.
        """
        missing_signals = self.db.query(Signal).outerjoin(
            VectorEmbedding, cast(Signal.id, String) == VectorEmbedding.id
        ).filter(VectorEmbedding.id == None).all()
        
        if not missing_signals:
            return 0
            
        count = 0
        for s in missing_signals:
            content = s.content.lower().strip()
            embedding = model.encode(content).tolist()
            
            vec = VectorEmbedding(
                id=str(s.id),
                embedding=embedding,
                metadata_={
                    "competitor_id": str(s.competitor_id) if s.competitor_id else None,
                    "category": s.category,
                    "content": content,
                    "timestamp": s.created_at.isoformat() if s.created_at else datetime.utcnow().isoformat()
                }
            )
            self.db.add(vec)
            count += 1
            
        self.db.commit()
        return count

    def run_clustering(self):
        """
        Runs HDBSCAN over all unclustered signals. 
        Requires joining signals with their respective vector embeddings.
        """
        # Step 1: Auto-Embed whatever the Teammate inserted into DB!
        synced_count = self.sync_missing_embeddings()
        print(f"Synced {synced_count} new direct DB signal insertions.")

        unclustered_signals = self.db.query(Signal).filter(Signal.cluster_id == None).all()
        if not unclustered_signals or len(unclustered_signals) < 3:
            return "Not enough data points to form new clusters."

        signal_ids = [str(s.id) for s in unclustered_signals]
        vectors = self.db.query(VectorEmbedding).filter(VectorEmbedding.id.in_(signal_ids)).all()
        vector_dict = {v.id: v.embedding for v in vectors}

        embeddings = []
        valid_signals = []
        for s in unclustered_signals:
            sid = str(s.id)
            if sid in vector_dict:
                embeddings.append(vector_dict[sid])
                valid_signals.append(s)
                
        if len(embeddings) < 3:
            return "Not enough embeddings found."

        embeddings_np = np.array(embeddings)
        
        clusterer = hdbscan.HDBSCAN(min_cluster_size=3, metric='euclidean')
        labels = clusterer.fit_predict(embeddings_np)

        cluster_map = {}
        for idx, label in enumerate(labels):
            if label == -1: 
                continue
            c_label = f"cluster_{label}"
            if c_label not in cluster_map:
                cluster_map[c_label] = []
            cluster_map[c_label].append(valid_signals[idx])

        for c_label, signals in cluster_map.items():
            cluster_id = f"CL_{uuid.uuid4().hex[:8]}"
            cluster = Cluster(
                id=cluster_id,
                label=signals[0].content[:50],
                description="Auto-generated semantic cluster"
            )
            self.db.add(cluster)
            
            # Update the source signals to belong to the new logical cluster
            for sig in signals:
                sig.cluster_id = cluster_id
                
        self.db.commit()
        return f"Created {len(cluster_map)} new clusters."
