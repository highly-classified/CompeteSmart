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

    def run_clustering(self):
        """
        Runs HDBSCAN over all unclustered signals. 
        Requires joining signals with their respective vector embeddings.
        """
        from src.models import Signal, VectorEmbedding, Cluster
        import numpy as np
        import hdbscan
        import uuid

        # Step 1: Retrieve unclustered signals
        unclustered_signals = self.db.query(Signal).filter(Signal.cluster_id == None).all()
        if not unclustered_signals or len(unclustered_signals) < 3:
            return "Not enough data points to form new clusters (need at least 3)."

        # Step 2: Retrieve embeddings for these signals
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
            return "Not enough valid embeddings found for clustering."

        embeddings_np = np.array(embeddings)
        
        # Step 3: Run HDBSCAN
        clusterer = hdbscan.HDBSCAN(min_cluster_size=3, metric='euclidean')
        labels = clusterer.fit_predict(embeddings_np)

        # Step 4: Map signals to clusters and persist
        cluster_map = {}
        for idx, label in enumerate(labels):
            if label == -1: # Noise
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
        return f"Created {len(cluster_map)} new clusters from {len(valid_signals)} signals."
