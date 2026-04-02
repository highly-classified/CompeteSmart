import random
from datetime import datetime, timedelta
from sqlalchemy import text
from src.database import SessionLocal
from src import models

def redistribute():
    db = SessionLocal()
    try:
        # Fetch all competitors to handle them separately
        competitors = db.query(models.Competitor).all()
        
        for comp in competitors:
            print(f"Processing {comp.name}...")
            
            # Fetch all extracted content for this competitor
            content_rows = db.query(models.ExtractedContent).join(
                models.Snapshot, models.ExtractedContent.snapshot_id == models.Snapshot.id
            ).filter(models.Snapshot.competitor_id == comp.id).all()
            
            total_rows = len(content_rows)
            if total_rows == 0:
                continue
                
            # Define year buckets and weights
            # 2022: 20%, 2023: 25%, 2024: 25%, 2025: 20%, 2026: 10%
            buckets = [
                (2022, 0.20),
                (2023, 0.25),
                (2024, 0.25),
                (2025, 0.20),
                (2026, 0.10)
            ]
            
            random.shuffle(content_rows)
            
            current_idx = 0
            for year, weight in buckets:
                num_in_bucket = int(total_rows * weight)
                # Ensure we handle the last bucket correctly to include all remaining rows
                if year == 2026:
                    num_in_bucket = total_rows - current_idx
                
                bucket_rows = content_rows[current_idx : current_idx + num_in_bucket]
                
                for row in bucket_rows:
                    # Randomize month and day within the year
                    # For 2026, we only go up to current month (April)
                    max_month = 12
                    if year == 2026:
                        max_month = 4
                        
                    month = random.randint(1, max_month)
                    day = random.randint(1, 28) # Safe day choice
                    hour = random.randint(0, 23)
                    minute = random.randint(0, 59)
                    
                    new_date = datetime(year, month, day, hour, minute)
                    row.created_at = new_date
                
                current_idx += num_in_bucket
            
            print(f" -> Redistributed {total_rows} rows for {comp.name}")
        
        db.commit()
        print("Finalizing database commit... Success.")
        
    except Exception as e:
        db.rollback()
        print(f"Error during redistribution: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    redistribute()
