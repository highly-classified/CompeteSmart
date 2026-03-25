import os
import json

def process_decisions(insights):
    """
    DECISION LAYER LOGIC:
    Takes consolidated insights from the Intelligence Layer (cluster_id, cluster_name, saturation, trend, whitespace)
    and computes Insight Prioritization and Experiment Recommendation.
    """
    decisions = []
    
    for insight in insights:
        cluster_id = insight.get("cluster_id")
        cluster = insight.get("cluster_name", "Unknown Cluster")
        
        # Guard against None values
        saturation = float(insight.get("saturation", 0.0) or 0.0)
        trend = float(insight.get("trend", 0.0) or 0.0)
        
        # Whitespace handling
        whitespace_personas = insight.get("whitespace_personas", [])
        if isinstance(whitespace_personas, str):
            whitespace_personas = [p.strip() for p in whitespace_personas.split(",")]
            
        # 1. INSIGHT PRIORITIZATION
        priority_score = (trend * 0.6) + ((1 - saturation) * 0.4)
        
        if priority_score >= 0.6:
            priority_label = "High Priority"
        elif priority_score >= 0.3:
            priority_label = "Medium Priority"
        else:
            priority_label = "Low Priority"
            
        # 2. EXPERIMENT RECOMMENDATION & COUNTERFACTUAL
        if whitespace_personas and len(whitespace_personas) > 0:
            target_persona = whitespace_personas[0]
            experiment = f"Test {target_persona}-focused pricing with relevant messaging in '{cluster}' to capture untapped segment."
            cf_explore = f"High differentiation by targeting {target_persona}, strong growth potential in a whitespace."
        else:
            target_persona = "niche sub-segments"
            experiment = f"Develop messaging for {target_persona} to differentiate within the fully saturated '{cluster}' space."
            cf_explore = f"Moderate differentiation by drilling down into specific {target_persona}, avoiding broad competition."
            
        counterfactual = {
            "follow_competitors": "High competition, low differentiation. Likely leads to price wars and high CAC.",
            "explore_whitespace": cf_explore
        }
        
        decisions.append({
            "cluster_id": cluster_id,
            "cluster_name": cluster,
            "priority_score": round(priority_score, 2),
            "priority": priority_label,
            "experiment": experiment,
            "counterfactual": counterfactual
        })
        
    return decisions
