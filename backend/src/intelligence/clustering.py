import hashlib
import numpy as np
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
        Runs HDBSCAN (with KMeans fallback) over all unclustered signals. 
        """
        from src.models import Signal, VectorEmbedding, Cluster
        import numpy as np
        import uuid
        import logging

        logger = logging.getLogger(__name__)

        # Step 1: Retrieve unclustered signals
        # Only process signals that have NOT been assigned to a cluster yet
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
        
        # Step 3: Run Clustering (HDBSCAN with KMeans fallback)
        labels = None
        try:
            import hdbscan
            logger.info("[Clustering] Attempting HDBSCAN...")
            clusterer = hdbscan.HDBSCAN(min_cluster_size=3, metric='euclidean')
            labels = clusterer.fit_predict(embeddings_np)
        except (ImportError, Exception) as e:
            logger.warning(f"[Clustering] HDBSCAN failed or not installed: {e}. Falling back to KMeans.")
            try:
                from sklearn.cluster import KMeans
                # Aim for approx signals/5 clusters, min 2, max 10 for demo purposes
                n_clusters = max(2, min(10, len(embeddings_np) // 5))
                kmeans = KMeans(n_clusters=n_clusters, random_state=42)
                labels = kmeans.fit_predict(embeddings_np)
            except Exception as ke:
                logger.error(f"[Clustering] KMeans fallback also failed: {ke}. Skipping clustering.")
                return f"Clustering failed: {ke}"

        # Step 4: Map signals to clusters and persist
        cluster_map = {}
        noise_signals = []
        
        for idx, label in enumerate(labels):
            if label == -1: # HDBSCAN Noise
                noise_signals.append(valid_signals[idx])
                continue
                
            c_label = f"cluster_{label}"
            if c_label not in cluster_map:
                cluster_map[c_label] = []
            cluster_map[c_label].append(valid_signals[idx])

        # Handle Noise Signals explicitly
        if noise_signals:
            logger.info(f"[Clustering] Flagging {len(noise_signals)} signals as 'noise'.")
            for sig in noise_signals:
                sig.cluster_id = "noise"

        # Handle valid clusters
        for c_label, signals in cluster_map.items():
            cluster_id = f"CL_{uuid.uuid4().hex[:8]}"
            cluster = Cluster(
                id=cluster_id,
                label=signals[0].content[:50],
                description=f"Auto-generated semantic cluster ({len(signals)} signals)"
            )
            self.db.add(cluster)
            
            # Update the source signals to belong to the new logical cluster
            for sig in signals:
                sig.cluster_id = cluster_id
                
        self.db.commit()
        return f"Created {len(cluster_map)} new clusters from {len(valid_signals)} signals ({len(noise_signals)} marked as noise)."
