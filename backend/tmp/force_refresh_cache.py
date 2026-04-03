import sys
import os

# Add the project root to sys.path
sys.path.append(os.getcwd())

from src.database import SessionLocal
from src.cache_manager import refresh_dashboard_cache

def force_refresh():
    db = SessionLocal()
    try:
        print("Forcing Dashboard Cache Refresh with Dynamic Themes...")
        refresh_dashboard_cache(db)
        print("Cache refreshed successfully!")
    except Exception as e:
        print(f"Failed to refresh cache: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    force_refresh()
