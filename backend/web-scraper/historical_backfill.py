import os
import sys
import json
import random
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Set database connection explicitly for standalone script
DATABASE_URL = "postgresql://neondb_owner:npg_y1zAFEGDUB3n@ep-morning-flower-a1adqnw7-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.models import Competitor, Snapshot, ExtractedContent, Signal

def random_date(start, end):
    return start + timedelta(seconds=random.randint(0, int((end - start).total_seconds())))

def get_weighted_random_date():
    now = datetime(2026, 4, 3, 0, 45) # Using current system time
    rand_val = random.random()
    if rand_val < 0.6:
        # Last 1 year (recent)
        start = now - timedelta(days=365)
        return random_date(start, now)
    elif rand_val < 0.9:
        # Mid (2023 to 2024/2025) - using 2023-01-01 up to 1 year ago
        start = datetime(2023, 1, 1)
        end = now - timedelta(days=365)
        if start >= end:
            start = datetime(2023, 1, 1)
            end = datetime(2023, 12, 31)
        return random_date(start, end)
    else:
        # Older (2022)
        start = datetime(2022, 1, 1)
        end = datetime(2022, 12, 31)
        return random_date(start, end)

def main():
    db = SessionLocal()
    result = {
        "run_status": "started",
        "updated_records": {
            "Housejoy": 0,
            "Sulekha": 0
        },
        "date_range": "2022-01-01 to present"
    }

    try:
        housejoy = db.query(Competitor).filter(Competitor.name == "Housejoy").first()
        sulekha = db.query(Competitor).filter(Competitor.name == "Sulekha").first()
        
        comps = {}
        if housejoy: comps["Housejoy"] = housejoy.id
        if sulekha: comps["Sulekha"] = sulekha.id

        # 0. One-time guard check restricted to our target competitors
        is_backfilled = db.query(ExtractedContent).join(Snapshot).filter(
            Snapshot.competitor_id.in_(list(comps.values())),
            ExtractedContent.created_at < datetime(2023, 1, 1)
        ).first()

        if is_backfilled:
            result["run_status"] = "skipped (already backfilled)"
            print(json.dumps(result, indent=2))
            return
        
        # We need to process each snapshot independently so they don't all get the same time
        for name, comp_id in comps.items():
            count = 0
            snapshots = db.query(Snapshot).filter(Snapshot.competitor_id == comp_id).all()
            for snap in snapshots:
                # generate a target date for the snapshot and all its extracted_content
                target_date = get_weighted_random_date()
                
                # Update Snapshot
                snap.created_at = target_date
                
                # Update ExtractedContent associated
                ext_contents = db.query(ExtractedContent).filter(ExtractedContent.snapshot_id == snap.id).all()
                for ext in ext_contents:
                    ext.created_at = target_date
                    count += 1
                    
                # Update Signal as well, if we want full consistency
                signals = db.query(Signal).filter(Signal.snapshot_id == snap.id).all()
                for sig in signals:
                    sig.created_at = target_date
                    
            result["updated_records"][name] = count

        db.commit()
        result["run_status"] = "completed"

    except Exception as e:
        db.rollback()
        result["run_status"] = "failed"
        result["error"] = str(e)
    finally:
        db.close()

    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
