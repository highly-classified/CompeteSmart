import os
import sys


sys.path.append(os.getcwd())

from src.database import SessionLocal
from src.models import Cluster, Signal

try:
    from src.intelligence.labeling import generate_clean_label
except ImportError:
    from src.labeling import generate_clean_label


def stabilize_labels():
    db = SessionLocal()
    updated_count = 0
    sample_labels = []

    try:
        clusters = db.query(Cluster).all()
        print(f"Recomputing clean labels for {len(clusters)} clusters...")

        for cluster in clusters:
            top_signals = (
                db.query(Signal)
                .filter(Signal.cluster_id == cluster.id)
                .order_by(Signal.confidence.desc(), Signal.created_at.desc(), Signal.id.desc())
                .limit(5)
                .all()
            )

            texts = [signal.content for signal in top_signals if signal.content]
            clean_label = generate_clean_label(texts) if texts else "General Service"
            cluster.clean_label = clean_label or "General Service"

            updated_count += 1
            if len(sample_labels) < 5:
                sample_labels.append(
                    {
                        "cluster_id": cluster.id,
                        "clean_label": cluster.clean_label,
                    }
                )

        db.commit()

        print(f"Updated {updated_count} clusters.")
        print("Sample updated labels:")
        for sample in sample_labels:
            print(f" - {sample['cluster_id']}: {sample['clean_label']}")

    except Exception as exc:
        db.rollback()
        print(f"Failed to stabilize labels: {exc}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    stabilize_labels()
