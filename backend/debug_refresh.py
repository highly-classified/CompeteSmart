from src.database import SessionLocal
from src.cache_manager import refresh_dashboard_cache
import logging
import sys

logging.basicConfig(level=logging.INFO, stream=sys.stdout)

def main():
    db = SessionLocal()
    try:
        refresh_dashboard_cache(db)
        print("Rebuild success.")
    except Exception as e:
        print(f"Rebuild failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    main()
