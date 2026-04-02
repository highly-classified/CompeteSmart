import os
import sys
import json
import random
import hashlib
from datetime import datetime, timedelta
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "postgresql://neondb_owner:npg_y1zAFEGDUB3n@ep-morning-flower-a1adqnw7-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.models import Competitor, Snapshot, ExtractedContent, Signal, Cluster, VectorEmbedding, Trend

import google.generativeai as genai
genai.configure(api_key="AIzaSyChXw2gbfc7t341rBp6XvJcUlc7g7XvHwo")

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

def get_cluster(db, category):
    cl = db.query(Cluster).filter(Cluster.id == category).first()
    if not cl:
        cl = Cluster(id=category, label=category.capitalize(), description=f"{category.capitalize()} services")
        db.add(cl)
        db.flush()
    return cl

def main():
    db = SessionLocal()
    competitors = ["Urban Company", "Housejoy", "Sulekha"]
    
    summary = {"Urban Company": 0, "Housejoy": 0, "Sulekha": 0}
    final_output = {"run_status": "started", "summary": summary}
    
    prefixes = ["NEW 2026: ", "Trending ", "Limited offer: ", "Just launched: "]
    services = ["AC Servicing", "Home Deep Cleaning", "Men's Grooming", "Painting", "Pest Control"]

    now = datetime(2026, 4, 3, 1, 10)
    
    try:
        for comp_name in competitors:
            log = {
                "competitor": comp_name,
                "new_records_added": 0,
                "duplicates_skipped": 0,
                "status": "started"
            }
            
            comp = db.query(Competitor).filter(Competitor.name == comp_name).first()
            if not comp:
                comp = Competitor(name=comp_name, domain="www.example.com", client_id=1)
                db.add(comp)
                db.flush()
            
            # Find latest timestamp
            latest_time = db.query(func.max(ExtractedContent.created_at)).join(Snapshot).filter(
                Snapshot.competitor_id == comp.id
            ).scalar()
            
            # CHECK SKIP CONDITION: If data was retrieved within the last day
            if latest_time and latest_time >= now - timedelta(days=1):
                log["status"] = "skipped (already fresh)"
                print(json.dumps(log))
                continue
                
            # Generate 5-10 records for last 7 days
            added = 0
            dupes = 0
            for i in range(random.randint(5, 10)):
                created_dt = now - timedelta(days=random.randint(0, 6), hours=random.randint(0, 23))
                srv = random.choice(services)
                prfx = random.choice(prefixes)
                
                content_text = f"{prfx} {srv} by {comp_name}. Price: INR {random.randint(300, 2500)}. Rating: 4.{random.randint(1,9)}"
                content_hsh = hash_content(content_text)
                
                # Deduplication check
                exists = db.query(ExtractedContent).filter(ExtractedContent.content_hash == content_hsh).first()
                if exists:
                    dupes += 1
                    continue
                
                snap = db.query(Snapshot).filter(Snapshot.competitor_id == comp.id).first()
                if not snap:
                    comp_url = "https://www.sulekha.com/home-services/" if comp_name == "Sulekha" else f"https://www.{comp_name.lower().replace(' ', '')}.com"
                    snap = Snapshot(competitor_id=comp.id, url=comp_url, created_at=created_dt)
                    db.add(snap)
                    db.flush()
                
                new_ext = ExtractedContent(snapshot_id=snap.id, content_type="service_info", content=content_text, content_hash=content_hsh, created_at=created_dt)
                db.add(new_ext)
                db.flush()
                
                cat = srv.lower().split(" ")[-1]
                cl = get_cluster(db, cat)
                
                new_sig = Signal(competitor_id=comp.id, snapshot_id=snap.id, content=content_text, category=cat, cluster_id=cl.id, created_at=created_dt)
                db.add(new_sig)
                db.flush()
                
                try:
                    emb = create_embeddings(content_text)
                    new_emb = VectorEmbedding(id=f"sig_{new_sig.id}_{random.randint(1,9999)}", embedding=emb, metadata_={"source": comp.name})
                    db.add(new_emb)
                except:
                    pass
                
                added += 1
                
            db.commit()
            
            # Step 7.4 Updates trends based on cluster
            db.query(Trend).delete()
            trends_data = db.query(
                Signal.cluster_id,
                func.date_trunc('month', Signal.created_at).label('month_yr'),
                func.count(Signal.id).label('freq')
            ).group_by(Signal.cluster_id, func.date_trunc('month', Signal.created_at)).all()
            for row in trends_data:
                if row.cluster_id:
                    trend = Trend(cluster_id=row.cluster_id, frequency=row.freq, growth_rate=row.freq*0.05, saturation=row.freq*0.02, calculated_at=row.month_yr)
                    db.add(trend)
            db.commit()
            
            log["status"] = "completed"
            log["new_records_added"] = added
            log["duplicates_skipped"] = dupes
            print(json.dumps(log))
            
            summary[comp_name] = added
            
        final_output["run_status"] = "completed"
        final_output["summary"] = summary
        
    except Exception as e:
        db.rollback()
        final_output["run_status"] = "failed"
        final_output["error"] = str(e)
    finally:
        db.close()

    print("\n--- FINAL OUTPUT ---")
    print(json.dumps(final_output, indent=2))

if __name__ == "__main__":
    main()
