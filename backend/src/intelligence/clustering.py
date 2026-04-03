import logging
import numpy as np
from datetime import datetime
from sqlalchemy import cast, String
from sqlalchemy.orm import Session
from src.labeling import generate_clean_label

logger = logging.getLogger(__name__)

class DataEmergentLabeler:
    @staticmethod
    def generate_clean_label(texts) -> str:
        return generate_clean_label(texts)

class ClusteringEngine:
    def __init__(self, db: Session):
        self.db = db

    def _get_signal_vectors(self, signals, vector_dict):
        embeddings = []
        valid_signals = []
        for signal in signals:
            signal_id = str(signal.id)
            if signal_id in vector_dict:
                embeddings.append(vector_dict[signal_id])
                valid_signals.append(signal)
        return embeddings, valid_signals

    def _create_cluster_for_signals(self, signals, cluster_id=None):
        from src.models import Cluster
        import uuid

        if not signals:
            return None

        cluster_id = cluster_id or f"CL_{uuid.uuid4().hex[:8]}"
        best_signal = sorted(signals, key=lambda s: getattr(s, "confidence", 1.0), reverse=True)[0]
        top_signals = [
            signal.content
            for signal in sorted(
                signals,
                key=lambda s: (
                    getattr(s, "confidence", 1.0),
                    getattr(s, "created_at", None) or datetime.min,
                ),
                reverse=True,
            )[:5]
        ]
        clean_label = DataEmergentLabeler.generate_clean_label(top_signals)

        cluster = Cluster(
            id=cluster_id,
            label=best_signal.content[:50],
            clean_label=clean_label,
            description=f"Auto-generated semantic cluster ({len(signals)} signals)",
        )
        self.db.add(cluster)

        for signal in signals:
            signal.cluster_id = cluster_id

        return cluster_id

    def _get_cluster_centroids(self, exclude_signal_ids=None):
        from src.models import Signal, VectorEmbedding

        exclude_signal_ids = set(str(signal_id) for signal_id in (exclude_signal_ids or []))
        clustered_signals = (
            self.db.query(Signal, VectorEmbedding)
            .join(VectorEmbedding, cast(Signal.id, String) == VectorEmbedding.id)
            .filter(Signal.cluster_id.isnot(None))
            .all()
        )

        cluster_vectors = {}
        for signal, vector in clustered_signals:
            if signal.cluster_id == "noise" or str(signal.id) in exclude_signal_ids:
                continue
            cluster_vectors.setdefault(signal.cluster_id, []).append(np.array(vector.embedding))

        centroids = {}
        for cluster_id, vectors in cluster_vectors.items():
            if vectors:
                centroids[cluster_id] = np.mean(vectors, axis=0)
        return centroids

    def _assign_to_nearest_clusters(self, signals, vector_dict, centroids):
        assigned = 0
        if not centroids:
            return assigned

        cluster_ids = list(centroids.keys())
        centroid_vectors = [centroids[cluster_id] for cluster_id in cluster_ids]

        for signal in signals:
            embedding = vector_dict.get(str(signal.id))
            if embedding is None:
                continue

            distances = [
                float(np.linalg.norm(np.array(embedding) - centroid))
                for centroid in centroid_vectors
            ]
            nearest_index = int(np.argmin(distances))
            signal.cluster_id = cluster_ids[nearest_index]
            assigned += 1

        return assigned

    def run_clustering(self):
        """
        Runs HDBSCAN (with KMeans fallback) over all unclustered signals and
        backfills any remaining signals into valid clusters.
        """
        from src.models import Signal, VectorEmbedding
        from src.intelligence.embeddings import EmbeddingGenerator
        
        logger.info("[Clustering] Starting clustering operation...")

        embedding_generator = EmbeddingGenerator(self.db)
        generated_embeddings = embedding_generator.generate_embeddings()
        if generated_embeddings:
            logger.info(f"[Clustering] Generated {generated_embeddings} missing embeddings before clustering.")

        # Step 1: Retrieve unclustered signals
        unclustered_signals = self.db.query(Signal).filter(Signal.cluster_id == None).all()
        if not unclustered_signals:
            logger.info("[Clustering] No unclustered signals found.")
            return "No unclustered signals found."

        # Step 2: Retrieve embeddings for these signals
        signal_ids = [str(s.id) for s in unclustered_signals]
        vectors = self.db.query(VectorEmbedding).filter(VectorEmbedding.id.in_(signal_ids)).all()
        vector_dict = {v.id: v.embedding for v in vectors}

        embeddings, valid_signals = self._get_signal_vectors(unclustered_signals, vector_dict)
        if not valid_signals:
            logger.warning("[Clustering] Unclustered signals exist but none have embeddings.")
            return "Unclustered signals exist but none have embeddings."

        created_cluster_count = 0
        nearest_assignment_count = 0
        fallback_cluster_count = 0
        clustered_signal_ids = set()
        
        if len(embeddings) >= 3:
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
                    logger.error(f"[Clustering] KMeans fallback also failed: {ke}.")
                    labels = None

            if labels is not None:
                cluster_map = {}
                for idx, label in enumerate(labels):
                    if label == -1:
                        continue

                    c_label = f"cluster_{label}"
                    cluster_map.setdefault(c_label, []).append(valid_signals[idx])

                for signals in cluster_map.values():
                    self._create_cluster_for_signals(signals)
                    created_cluster_count += 1
                    clustered_signal_ids.update(str(signal.id) for signal in signals)

        remaining_embedded_signals = [
            signal for signal in valid_signals if str(signal.id) not in clustered_signal_ids
        ]

        if remaining_embedded_signals:
            centroids = self._get_cluster_centroids(exclude_signal_ids=signal_ids)
            nearest_assignment_count += self._assign_to_nearest_clusters(
                remaining_embedded_signals,
                vector_dict,
                centroids,
            )

        still_unclustered = self.db.query(Signal).filter(Signal.cluster_id == None).all()
        if still_unclustered:
            logger.info(f"[Clustering] Creating fallback clusters for {len(still_unclustered)} signals with no valid cluster assignment.")
            for signal in still_unclustered:
                self._create_cluster_for_signals([signal])
                fallback_cluster_count += 1

        self.db.commit()
        msg = (
            f"Created {created_cluster_count} clustered groups, assigned {nearest_assignment_count} signals "
            f"to nearest existing clusters, created {fallback_cluster_count} fallback clusters, and "
            f"processed {len(unclustered_signals)} unclustered signals total."
        )
        logger.info(f"[Clustering] {msg}")
        return msg
