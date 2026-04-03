import os
import json
import logging
from src.ml_model import MarketStrategyRanker

logger = logging.getLogger(__name__)

# Initialize the ranker
ranker = MarketStrategyRanker()

def process_decisions_ml(insights):
    """
    ML-DRIVEN DECISION LAYER:
    Takes consolidated insights from the Intelligence Layer and uses 
    a Random Forest model to rank experiments and select the Top 3.
    """
    candidates = []
    
    for insight in insights:
        cluster_id = insight.get("cluster_id")
        cluster_name = insight.get("cluster_name", "Unknown Cluster")
        
        # Extract features for ML model
        saturation = float(insight.get("saturation", 0.5) or 0.5)
        trend_momentum = float(insight.get("trend", 0.0) or 0.0) # Assume this is momentum (e.g. 0.96)
        
        # Risk score calculation (simplified for this POC or pulled from TrustLayer)
        # In a full integration, we'd pull the real Trust Score here.
        risk_score = 0.4 * saturation + 0.2 * (1.0 - trend_momentum) 
        
        evidence_count = len(insight.get("evidence", []))
        if evidence_count == 0:
            evidence_count = 1 # avoid log(0)
            
        # Strategy Recommendation (interpolated like original for matching JSON schema)
        whitespace_personas = insight.get("whitespace_personas", [])
        if isinstance(whitespace_personas, str):
            whitespace_personas = [p.strip() for p in whitespace_personas.split(",")]
            
        if whitespace_personas and len(whitespace_personas) > 0:
            target_persona = whitespace_personas[0]
            experiment = f"Test {target_persona}-focused pricing with relevant messaging in '{cluster_name}' to capture untapped segment."
        else:
            target_persona = "niche sub-segments"
            experiment = f"Develop messaging for {target_persona} to differentiate within the fully saturated '{cluster_name}' space."

        # Add to candidates for ranking, with the required features
        candidates.append({
            "cluster_id": cluster_id,
            "cluster_name": cluster_name,
            "momentum": trend_momentum,
            "saturation": saturation,
            "risk": risk_score,
            "evidence_count": evidence_count,
            "recommended_action": experiment,
            "priority": "High Priority" if trend_momentum > 0.6 else "Medium Priority" if trend_momentum > 0.3 else "Low Priority"
        })
        
    # RANK USING ML MODEL
    ranked_results = ranker.rank_experiments(candidates)
    
    # Format the data according to the "Locked Schema" expected by the backend
    final_output = []
    for row in ranked_results:
        # Map back to final output structure
        final_output.append({
            "insight": f"Cluster '{row['cluster_name']}' scored {row['ml_score']:.2f} by the Market Analysis ML Model.",
            "cluster_id": row['cluster_id'],
            "trend": row['priority'],
            "confidence": round(row['ml_score'], 2),
            "risk": row['risk'],
            "recommended_action": row['recommended_action'],
            "evidence": insight.get("evidence", []) if 'insight' in locals() else [] # evidence is already in candidates in full pipeline
        })
        
    return final_output
