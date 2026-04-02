from src.database import SessionLocal
from src.cache_manager import refresh_dashboard_cache
import logging
import sys
import traceback

logging.basicConfig(level=logging.INFO, stream=sys.stdout)

def main():
    db = SessionLocal()
    try:
        refresh_dashboard_cache(db)
        print("Rebuild success.")
    except Exception:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        print(f"FAILED TYPE: {exc_type}")
        print(f"FAILED VAL: {exc_value}")
        traceback.print_exc()
        # Full dump to file to avoid truncation
        with open("full_traceback.txt", "w") as f:
            traceback.print_exc(file=f)
    finally:
        db.close()

if __name__ == "__main__":
    main()
