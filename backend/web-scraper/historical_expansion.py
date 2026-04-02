import os
import sys
import json
import random
import hashlib
from datetime import datetime, timedelta
from sqlalchemy import create_engine, desc
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "postgresql://neondb_owner:npg_y1zAFEGDUB3n@ep-morning-flower-a1adqnw7-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.models import Competitor, Snapshot, ExtractedContent, Signal, Cluster, VectorEmbedding

import google.generativeai as genai
genai.configure(api_key="AIzaSyChXw2gbfc7t341rBp6XvJcUlc7g7XvHwo")
model = genai.GenerativeModel('gemini-2.5-flash')

def hash_content(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()

def create_embeddings(text):
    try:
        result = genai.embed_content(
            model="models/text-embedding-004",
            content=text,
            task_type="semantic_similarity"
        )
        return result['embedding']
    except Exception as e:
        return [0.0]*384

def get_random_date():
    now = datetime(2026, 4, 3, 0, 57)
    rand_val = random.random()
    if rand_val < 0.2:
        start, end = datetime(2022, 1, 1), datetime(2022, 12, 31)
    elif rand_val < 0.5:
        start, end = datetime(2023, 1, 1), datetime(2023, 12, 31)
    elif rand_val < 0.8:
        start, end = datetime(2024, 1, 1), datetime(2024, 12, 31)
    else:
        start, end = datetime(2025, 1, 1), now
    
    if start >= end:
        end = start + timedelta(days=1)
    return start + timedelta(seconds=random.randint(0, int((end - start).total_seconds())))

def main():
    db = SessionLocal()
    result = {
        "run_status": "started",
        "new_rows_added": {"Housejoy": 0, "Sulekha": 0},
        "total_rows_after": {"Housejoy": 0, "Sulekha": 0}
    }

    try:
        # Step 0: Check guard limit
        housejoy = db.query(Competitor).filter(Competitor.name == "Housejoy").first()
        sulekha = db.query(Competitor).filter(Competitor.name == "Sulekha").first()
        
        comps = {}
        if housejoy: comps["Housejoy"] = housejoy
        if sulekha: comps["Sulekha"] = sulekha

        total_rows_before = {}
        for name, comp in comps.items():
            cnt = db.query(ExtractedContent).join(Snapshot).filter(Snapshot.competitor_id == comp.id).count()
            total_rows_before[name] = cnt

        if total_rows_before.get("Housejoy", 0) > 30 or total_rows_before.get("Sulekha", 0) > 30:
            result["run_status"] = "skipped (already expanded)"
            result["total_rows_after"] = total_rows_before
            print(json.dumps(result, indent=2))
            return

        prefixes = ["Professional", "Affordable", "Quick", "Premium", "Reliable", "Expert", "Top-rated"]
        
        # Step 1: Base templates
        for name, comp in comps.items():
            base_rows = db.query(ExtractedContent).join(Snapshot).filter(Snapshot.competitor_id == comp.id).all()
            
            new_added = 0
            for row in base_rows:
                # Get cluster or signal info
                sig = db.query(Signal).filter(Signal.snapshot_id == row.snapshot_id, Signal.content == row.content).first()
                cat = sig.category if sig else "service"
                cluster_id = sig.cluster_id if sig else None
                
                num_new = random.randint(3, 5)
                for _ in range(num_new):
                    random_date_val = get_random_date()
                    
                    # Create variations
                    prefix = random.choice(prefixes)
                    new_content = f"[{prefix}] {row.content}"
                    content_hash = hash_content(new_content + str(random_date_val.timestamp()) + str(random.random()))
                    
                    orig_snap = db.query(Snapshot).filter(Snapshot.id == row.snapshot_id).first()
                    
                    # New snapshot per variation as requested
                    new_snap = Snapshot(competitor_id=comp.id, url=orig_snap.url if orig_snap else "https://unknown.com", created_at=random_date_val)
                    db.add(new_snap)
                    db.flush()
                    
                    # New extracted content
                    new_ext = ExtractedContent(
                        snapshot_id=new_snap.id, 
                        content_type=row.content_type, 
                        content=new_content, 
                        content_hash=content_hash,
                        created_at=random_date_val
                    )
                    db.add(new_ext)
                    db.flush()
                    
                    # Pipeline
                    if sig:
                        new_sig = Signal(competitor_id=comp.id, snapshot_id=new_snap.id, content=new_content, category=cat, cluster_id=cluster_id, created_at=random_date_val)
                        db.add(new_sig)
                        db.flush()
                        
                        try:
                            # Use random mock vectors or simple generation
                            emb = create_embeddings(new_content)
                            vec = VectorEmbedding(id=f"sig_{new_sig.id}_{random.randint(100, 9999)}", embedding=emb, metadata_={"source": comp.name, "type": "signal"})
                            db.add(vec)
                        except:
                            pass
                    
                    new_added += 1
            
            result["new_rows_added"][name] = new_added
            result["total_rows_after"][name] = total_rows_before[name] + new_added

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
