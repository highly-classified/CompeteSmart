from src.database import SessionLocal
from sqlalchemy import text

def add_index():
    db = SessionLocal()
    try:
        db.execute(text("CREATE INDEX IF NOT EXISTS idx_signals_cluster_id ON signals(cluster_id);"))
        db.commit()
        print("Index created successfully.")
    except Exception as e:
        print(f"Error creating index: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    add_index()
