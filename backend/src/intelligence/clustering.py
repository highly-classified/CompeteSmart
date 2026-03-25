import hashlib
import numpy as np
import hdbscan
from sentence_transformers import SentenceTransformer
from sqlalchemy.orm import Session
from src.models import ExtractedSignal, SignalCluster
import uuid

# Load local embedding model (free, offline)
model = SentenceTransformer('all-MiniLM-L6-v2')

class ClusteringEngine:
    def __init__(self, db: Session):
        self.db = db

    def clean_text(self, text: str) -> str:
        # Lowercase and strip spaces
        return text.lower().strip()

    def generate_hash(self, text: str) -> str:
        # MD5 or SHA256 for deterministic hashing
        return hashlib.sha256(text.encode('utf-8')).hexdigest()

    def process_new_signals(self, raw_signals: list[dict]):
        """
        Input: list of dicts with competitor_id, timestamp, signal_type, content
        Creates embeddings and stores to vector DB
        """
        processed = []
        for signal in raw_signals:
            content = self.clean_text(signal["content"])
            content_hash = self.generate_hash(content)
            
            # Deduplication check
            exists = self.db.query(ExtractedSignal).filter(ExtractedSignal.content_hash == content_hash).first()
            if exists:
                continue

            # Generate Sentence Embedding
            embedding = model.encode(content).tolist()
            
            new_signal = ExtractedSignal(
                competitor_id=signal["competitor_id"],
                timestamp=signal["timestamp"],
                signal_type=signal["signal_type"],
                content=content,
                content_hash=content_hash,
                embedding=embedding
            )
            self.db.add(new_signal)
            processed.append(new_signal)
        
        self.db.commit()
        return processed

    def run_clustering(self):
        """
        Runs HDBSCAN over all unclustered signals to group semantic similarities.
        """
        signals = self.db.query(ExtractedSignal).filter(ExtractedSignal.cluster_id == None).all()
        if not signals or len(signals) < 3:
            return "Not enough data points to form new clusters."

        embeddings = np.array([sig.embedding for sig in signals])
        
        # HDBSCAN Clustering. metric='euclidean' since MiniLM vectors perform well with it.
        clusterer = hdbscan.HDBSCAN(min_cluster_size=3, metric='euclidean')
        labels = clusterer.fit_predict(embeddings)

        # Process clusters
        cluster_dict = {}
        for idx, label in enumerate(labels):
            if label == -1: # Outliers/Noise
                continue
                
            cluster_id = f"CL_{label}"
            if cluster_id not in cluster_dict:
                cluster_dict[cluster_id] = []
            cluster_dict[cluster_id].append(signals[idx])

        # Assign records to clusters and compute centroids
        for _, cluster_signals in cluster_dict.items():
            cluster_embeddings = np.array([s.embedding for s in cluster_signals])
            # Centroid = mean vector of the cluster
            centroid_vector = np.mean(cluster_embeddings, axis=0).tolist()
            
            unique_cid = f"CL_{uuid.uuid4().hex[:8]}"
            cluster = SignalCluster(
                id=unique_cid,
                centroid_vector=centroid_vector,
                label=cluster_signals[0].content[:50] # Placeholder: LLM can label this later
            )
            self.db.add(cluster)
            
            for sig in cluster_signals:
                sig.cluster_id = unique_cid
                
        self.db.commit()
        return f"Created {len(cluster_dict)} new clusters."
