import os
import json
import psycopg2
from psycopg2.extras import RealDictCursor

# Connect to the exact database provided by the user
# Fallback to the environment variable if needed in production
DATABASE_URL = os.environ.get(
    "DATABASE_URL", 
    "postgresql://neondb_owner:npg_y1zAFEGDUB3n@ep-morning-flower-a1adqnw7-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"
)

def fetch_intelligence_insights(conn):
    """
    INPUT FROM INTELLIGENCE LAYER:
    Fetches pre-processed data (Saturation, Whitespace, Persona Drift) 
    that the Intelligence Layer has already clustered and calculated.
    """
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    # Target table populated by the Intelligence Layer
    query = """
        SELECT 
            cluster_name, 
            saturation, 
            trend, 
            whitespace_personas
        FROM intelligence_insights
    """
    cursor.execute(query)
    return cursor.fetchall()


def process_decisions(insights):
    """
    DECISION LAYER LOGIC:
    Only handles Insight Prioritization and Experiment Recommendation.
    (Trust Layer handles Risk & Traceability; Intelligence Layer handles Clustering & Trends)
    """
    decisions = []
    
    for insight in insights:
        cluster = insight["cluster_name"]
        saturation = float(insight["saturation"])
        trend = float(insight["trend"])
        
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
            "cluster": cluster,
            "priority_score": round(priority_score, 2),
            "priority": priority_label,
            "experiment": experiment,
            "counterfactual": counterfactual
        })
        
    return decisions


def save_decisions(conn, decisions):
    """
    OUTPUT TO POSTGRES
    Saves the output from the Decision Layer into the DB 
    so the Output & Trust layers can read from it.
    """
    cursor = conn.cursor()
    for decision in decisions:
        cursor.execute(
            """
            INSERT INTO decision_outputs (cluster_name, priority_score, priority_label, experiment, counterfactual)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (cluster_name) DO UPDATE 
            SET priority_score = EXCLUDED.priority_score,
                priority_label = EXCLUDED.priority_label,
                experiment = EXCLUDED.experiment,
                counterfactual = EXCLUDED.counterfactual
            """,
            (
                decision["cluster"], 
                decision["priority_score"], 
                decision["priority"], 
                decision["experiment"], 
                json.dumps(decision["counterfactual"])
            )
        )
    conn.commit()


def main():
    print("Connecting to PostgreSQL Database...")
    try:
        conn = psycopg2.connect(DATABASE_URL)
        print("Connected successfully.")
        
        print("Fetching Intelligence Layer insights...")
        insights = fetch_intelligence_insights(conn)
        
        if not insights:
            print("No insights found from Intelligence Layer in DB.")
        else:
            print(f"Processing decisions for {len(insights)} clusters...")
            decisions = process_decisions(insights)
            
            print("Saving Decision Layer output back to DB...")
            save_decisions(conn, decisions)
            
            print("\n--- DECISION LAYER OUTPUT LOG ---\n")
            print(json.dumps(decisions, indent=2))
        
    except psycopg2.Error as e:
        print(f"Database operation failed. (This is expected if tables are not set up yet)")
        print(f"Error Details: {e}")
    finally:
        if 'conn' in locals() and conn:
            conn.close()
            print("Database connection closed.")


if __name__ == "__main__":
    main()
