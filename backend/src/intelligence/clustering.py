import logging
import numpy as np
import re
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

class DataEmergentLabeler:
    @staticmethod
    def generate_clean_label(content: str) -> str:
        if not content:
            return ""
        
        # 1. Basic Cleaning & Lowercase
        text = content.lower()
        
        # 2. Remove ratings, prices, numbers (e.g. 4.81, 61k reviews, 2 bathrooms, 30-min)
        # Remove (61k reviews) and similar
        text = re.sub(r'\(?\d+[\.\d]*[k]?\s*reviews\)?', '', text)
        # Remove digits and common number fragments
        text = re.sub(r'\d+[\.\d]*', '', text)
        
        # Remove punctuation except spaces
        text = re.sub(r'[^\w\s]', ' ', text)
        
        # 3. Stopwords & Filler removal
        stopwords = {"the", "is", "and", "for", "with", "your", "to", "of", "at", "on", "in", "my", "near", "me", "i", "am", "a"}
        fillers = {"great", "best", "professional", "service", "services", "home", "quality", "satisfied", "doorstep", "urban", "value", "money"}
        
        words = text.split()
        
        # 4. Filtering for meaningful words
        meaningful_words = []
        for w in words:
            if len(w) >= 3 and w not in stopwords and w not in fillers:
                meaningful_words.append(w)
        
        # 5. Selection (1-2 words max)
        final_words = meaningful_words[:2]
        result = " ".join(final_words).title().strip()
        
        # 6. Strict Validation
        # Ignore if: empty, > 30 chars, or original was a full sentence (> 10 words)
        if not result or len(result) > 30 or len(words) > 10:
            return ""
            
        return result

class ClusteringEngine:
    def __init__(self, db: Session):
        self.db = db

    def run_clustering(self):
        """
        Runs HDBSCAN (with KMeans fallback) over all unclustered signals. 
        """
        from src.models import Signal, VectorEmbedding, Cluster
        import uuid
        
        logger.info("[Clustering] Starting clustering operation...")

        # Step 1: Retrieve unclustered signals
        unclustered_signals = self.db.query(Signal).filter(Signal.cluster_id == None).all()
        if not unclustered_signals or len(unclustered_signals) < 3:
            logger.info("[Clustering] Not enough data points to form new clusters (need at least 3).")
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
            logger.info("[Clustering] Not enough valid embeddings found for clustering.")
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
            
            # Step 1: Select best signal (highest confidence)
            best_signal = sorted(signals, key=lambda s: getattr(s, 'confidence', 1.0), reverse=True)[0]
            
            # Step 2-5: Generate label from data
            clean_label = DataEmergentLabeler.generate_clean_label(best_signal.content)
            
            cluster = Cluster(
                id=cluster_id,
                label=best_signal.content[:50],
                clean_label=clean_label,
                description=f"Auto-generated semantic cluster ({len(signals)} signals)"
            )
            self.db.add(cluster)
            
            # Update the source signals to belong to the new logical cluster
            for sig in signals:
                sig.cluster_id = cluster_id
                
        self.db.commit()
        msg = f"Created {len(cluster_map)} new clusters from {len(valid_signals)} signals ({len(noise_signals)} marked as noise)."
        logger.info(f"[Clustering] {msg}")
        return msg
