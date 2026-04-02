from src.database import SessionLocal
from sqlalchemy import text

def verify_cache():
    db = SessionLocal()
    try:
        results = db.execute(text("SELECT key, last_updated FROM dashboard_cache")).fetchall()
        print(f"Found {len(results)} cache entries:")
        for key, updated in results:
            print(f" - {key} (Updated: {updated})")
    finally:
        db.close()

if __name__ == "__main__":
    verify_cache()
