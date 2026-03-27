from sqlalchemy.orm import Session
from sqlalchemy import cast, String
from src.models import Signal, VectorEmbedding
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# Model: all-MiniLM-L6-v2 (384 dimensions)
_model = None

def get_model():
    global _model
    if _model is None:
        logger.info("[EmbeddingGeneration] Loading SentenceTransformer model (all-MiniLM-L6-v2)...")
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer('all-MiniLM-L6-v2')
        logger.info("[EmbeddingGeneration] Model loaded successfully.")
    return _model

class EmbeddingGenerator:
    def __init__(self, db: Session, batch_size: int = 64):
        self.db = db
        self.batch_size = batch_size

    def generate_embeddings(self) -> int:
        """
        Finds signals without embeddings, generates them in batches using all-MiniLM-L6-v2,
        and stores them in the `vector_embeddings` table.
        Ensures strict mapping with `signal_id`.
        """
        logger.info(f"[EmbeddingGeneration] Starting batch embedding generation (batch_size={self.batch_size})...")

        # Find signals that don't have an embedding yet
        missing_signals = self.db.query(Signal).outerjoin(
            VectorEmbedding, cast(Signal.id, String) == VectorEmbedding.id
        ).filter(VectorEmbedding.id == None).all()

        if not missing_signals:
            logger.info("[EmbeddingGeneration] No signals require new embeddings.")
            return 0

        count = 0
        total_missing = len(missing_signals)
        
        for i in range(0, total_missing, self.batch_size):
            batch = missing_signals[i : i + self.batch_size]
            contents = [s.content.lower().strip() for s in batch]
            
            try:
                # Generate Embeddings for the batch
                embeddings = get_model().encode(contents).tolist()
                
                for signal, embedding in zip(batch, embeddings):
                    # Store in vector_embeddings table
                    new_vec = VectorEmbedding(
                        id=str(signal.id),
                        embedding=embedding,
                        metadata_={
                            "competitor_id": str(signal.competitor_id) if signal.competitor_id else None,
                            "category": signal.category,
                            "content": signal.content,
                            "timestamp": datetime.utcnow().isoformat()
                        }
                    )
                    self.db.add(new_vec)
                    count += 1
                
                self.db.commit()
                logger.info(f"[EmbeddingGeneration] Processed batch {i//self.batch_size + 1}: {len(batch)} signals.")
                
            except Exception as e:
                self.db.rollback()
                logger.error(f"[EmbeddingGeneration] Failed to process batch at index {i}: {e}. Retrying individual signals...")
                # Fallback to individual processing for this batch if it failed
                for s in batch:
                    try:
                        emb = get_model().encode([s.content.lower().strip()])[0].tolist()
                        vec = VectorEmbedding(
                            id=str(s.id),
                            embedding=emb,
                            metadata_={
                                "competitor_id": str(s.competitor_id) if s.competitor_id else None,
                                "category": s.category,
                                "content": s.content,
                                "timestamp": datetime.utcnow().isoformat()
                            }
                        )
                        self.db.add(vec)
                        self.db.commit()
                        count += 1
                    except Exception as individual_e:
                        self.db.rollback()
                        logger.error(f"[EmbeddingGeneration] Signal {s.id} failed: {individual_e}")

        logger.info(f"[EmbeddingGeneration] Successfully generated {count} embeddings.")
        return count
