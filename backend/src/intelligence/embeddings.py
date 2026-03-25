from sentence_transformers import SentenceTransformer
from sqlalchemy.orm import Session
from sqlalchemy import cast, String
from src.models import Signal, VectorEmbedding
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# Model: all-MiniLM-L6-v2 (384 dimensions)
model = SentenceTransformer('all-MiniLM-L6-v2')

class EmbeddingGenerator:
    def __init__(self, db: Session):
        self.db = db

    def generate_embeddings(self) -> int:
        """
        Finds signals without embeddings, generates them using all-MiniLM-L6-v2,
        and stores them in the `vector_embeddings` table.
        Ensures strict mapping with `signal_id`.
        """
        logger.info("[EmbeddingGeneration] Starting embedding generation for new signals...")

        # Find signals that don't have an embedding yet
        # Join Signal.id (Integer) with VectorEmbedding.id (String)
        missing_signals = self.db.query(Signal).outerjoin(
            VectorEmbedding, cast(Signal.id, String) == VectorEmbedding.id
        ).filter(VectorEmbedding.id == None).all()

        if not missing_signals:
            logger.info("[EmbeddingGeneration] No signals require new embeddings.")
            return 0

        count = 0
        for signal in missing_signals:
            content = signal.content.lower().strip()
            if not content:
                continue

            # Generate Embedding (384 dimensions)
            embedding = model.encode(content).tolist()

            # Store in vector_embeddings table
            new_vec = VectorEmbedding(
                id=str(signal.id),
                embedding=embedding,
                metadata_={
                    "competitor_id": str(signal.competitor_id) if signal.competitor_id else None,
                    "category": signal.category,
                    "content": content,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
            self.db.add(new_vec)
            count += 1

        self.db.commit()
        logger.info(f"[EmbeddingGeneration] Successfully generated {count} embeddings.")
        return count
