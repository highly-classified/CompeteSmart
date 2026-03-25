import os
import json
import logging
import asyncio
import sys
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)-8s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("PipelineRunner")

# Flags
RUN_SCRAPER = True
RUN_SEED = False
RUN_ANALYSIS = True

# Add backend and web-scraper to sys.path to ensure imports work correctly
sys.path.append(os.path.join(os.getcwd(), "web-scraper"))

from src.database import SessionLocal, engine
from src import models
from src.intelligence.signal_extraction import SignalExtractor
from src.intelligence.embeddings import EmbeddingGenerator
from src.intelligence.clustering import ClusteringEngine
from src.intelligence.temporal import TemporalEngine
from src.intelligence.advanced import AdvancedIntelligenceEngine
from src.trust_layer import compute_trust_score
from decision_layer import process_decisions

# Data Layer (web-scraper)
import db
import scheduler
import seed_history

async def main():
    logger.info("--- STARTING END-TO-END MARKET INTELLIGENCE PIPELINE ---")
    
    # 0. Initialize Database
    logger.info("[Step 0] Initializing database schema...")
    db.init_db() # Psycopg2 init
    models.Base.metadata.create_all(bind=engine) # SQLAlchemy init
    
    # 1. Data Ingestion
    if RUN_SCRAPER:
        logger.info("[Step 1] Running Scraper Cycle...")
        try:
            url_map = scheduler._build_url_map()
            await scheduler.run_cycle(url_map, force=False)
        except Exception as e:
            logger.error(f"Scraper failed: {e}")
            # Continue to analysis if requested, maybe we have old data
            
    if RUN_SEED:
        logger.info("[Step 2] Running Synthetic History Seeding...")
        try:
            seed_history.seed()
        except Exception as e:
            logger.error(f"Seeding failed: {e}")

    if not RUN_ANALYSIS:
        logger.info("RUN_ANALYSIS is False. Pipeline stopping after ingestion.")
        return

    # Initialize SQLAlchemy Session
    session = SessionLocal()
    
    try:
        # 3. Signal Extraction
        logger.info("[Step 3] Extracting Signals...")
        extractor = SignalExtractor(session)
        signals_count = extractor.extract_signals()
        logger.info(f" -> Extracted {signals_count} new signals.")
        
        # Data Validation
        total_signals = session.query(models.Signal).count()
        if total_signals == 0:
            logger.warning("No signals found in database. Stopping analysis pipeline.")
            return

        # 4. Embedding Generation
        logger.info("[Step 4] Generating Embeddings...")
        embedder = EmbeddingGenerator(session)
        embeddings_count = embedder.generate_embeddings()
        logger.info(f" -> Generated {embeddings_count} new embeddings.")

        # 5. Semantic Clustering
        logger.info("[Step 5] Running Semantic Clustering (HDBSCAN)...")
        cluster_engine = ClusteringEngine(session)
        cluster_result = cluster_engine.run_clustering()
        logger.info(f" -> Clustering result: {cluster_result}")
        
        # Data Validation
        total_clusters = session.query(models.Cluster).count()
        if total_clusters == 0:
            logger.warning("No clusters formed. Stopping analysis pipeline.")
            return

        # 6. Temporal & Advanced Analysis
        logger.info("[Step 6] Running Temporal & Advanced Analysis...")
        temp_engine = TemporalEngine(session)
        adv_engine = AdvancedIntelligenceEngine(session)
        
        trends = temp_engine.calculate_trends()
        logger.info(f" -> Calculated trends for {len(trends)} clusters.")
        
        saturations = temp_engine.calculate_saturation()
        logger.info(f" -> Calculated saturation for {len(saturations)} clusters.")
        
        whitespaces = adv_engine.detect_whitespace()
        logger.info(f" -> Detected {len(whitespaces)} whitespace themes.")
        
        # 7. Trust Layer & Decision Layer Preparation
        logger.info("[Step 7] Applying Trust Layer and Preparing Decision Inputs...")
        
        insights = []
        for t in trends:
            c_id = t["cluster_id"]
            s_match = next((s for s in saturations if s["cluster_id"] == c_id), None)
            sat_score = s_match["saturation_score"] if s_match else 0.0
            
            # Map detected whitespace vectors into themes (simulated here)
            w_personas = ["budget-conscious", "untapped-niche"] if whitespaces else []
            
            insights.append({
                "cluster_id": c_id,
                "cluster_name": t["cluster_label"] or "Untitled Cluster",
                "trend": t["growth_rate"],
                "saturation": sat_score,
                "whitespace_personas": w_personas
            })
            
        if not insights:
            logger.warning("No insights consolidated. Stopping pipeline.")
            return

        # 8. Decision Layer
        logger.info("[Step 8] Running Decision Layer...")
        decisions = process_decisions(insights)
        logger.info(f" -> Generated {len(decisions)} experiment recommendations.")
        
        # Consolidate with Trust Scores
        final_output = []
        for decision in decisions:
            cluster_id = decision["cluster_id"]
            trust_output = compute_trust_score(
                cluster_id=cluster_id, 
                experiment=decision["experiment"], 
                client_positioning="premium"
            )
            
            final_output.append({
                "cluster_id": cluster_id,
                "cluster_name": decision["cluster_name"],
                "decision": {
                    "priority": decision["priority"],
                    "priority_score": decision["priority_score"],
                    "experiment": decision["experiment"],
                    "counterfactual": decision["counterfactual"]
                },
                "trust_layer": trust_output,
                "timestamp": datetime.utcnow().isoformat()
            })
            
        # Save to JSON
        output_path = "decision_layer_output.json"
        with open(output_path, "w") as f:
            json.dump(final_output, f, indent=2)
            
        logger.info(f"--- PIPELINE COMPLETE ✓ Output saved to {output_path} ---")

    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
    finally:
        session.close()

if __name__ == "__main__":
    asyncio.run(main())
