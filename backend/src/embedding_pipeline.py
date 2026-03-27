import os
import psycopg2
from psycopg2.extras import DictCursor, execute_batch
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Singleton model definition
MODEL_NAME = "all-MiniLM-L6-v2"
_model = None

def get_model():
    """Returns the loaded sentence transformer model (singleton)."""
    global _model
    if _model is None:
        print(f"Loading embedding model '{MODEL_NAME}'...")
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(MODEL_NAME)
    return _model

def initialize_database(conn):
    """Creates the necessary schemas and extensions for vector embeddings."""
    with conn.cursor() as cur:
        # Enable pgvector if not already enabled
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        # Create signal_embeddings table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS signal_embeddings (
                id INTEGER PRIMARY KEY,
                embedding vector(384),
                content TEXT,
                competitor_id INTEGER,
                cluster_id TEXT,
                category TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
    conn.commit()

def run_embedding_pipeline(batch_size: int = 50) -> None:
    """
    Fetches unprocessed records from the 'signals' table, computes embeddings
    for their content, and strictly inserts them into 'signal_embeddings'.
    """
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("Error: DATABASE_URL environment variable is missing.")
        return

    conn = None
    try:
        conn = psycopg2.connect(db_url)
        initialize_database(conn)
        
        # Warm up the model once
        transformer = get_model()
        
        with conn.cursor(cursor_factory=DictCursor) as cur:
            # 1. Fetch Unprocessed Signals via LEFT JOIN
            cur.execute("""
                SELECT s.id, s.content, s.competitor_id, s.cluster_id, s.category
                FROM signals s
                LEFT JOIN signal_embeddings e ON s.id = e.id
                WHERE e.id IS NULL
                LIMIT %s;
            """, (batch_size,))
            
            rows = cur.fetchall()
            
            if not rows:
                print("No new signals found.")
                return
                
            print(f"Fetched {len(rows)} unprocessed signals. Generating embeddings...")
            
            # 2. Generate Embeddings & Assemble Insert Batch
            insert_data = []
            for row in rows:
                content = row['content']
                
                # Skip rows with empty or completely whitespace-only content
                if not content or not content.strip():
                    continue
                    
                try:
                    # Convert to literal "[x, y, ...]" representation for direct parameter mapping
                    embedding_list = transformer.encode(content).tolist()
                    embedding_str = "[" + ",".join(map(str, embedding_list)) + "]"
                    
                    insert_data.append((
                        row['id'],
                        embedding_str,
                        content,
                        row['competitor_id'],
                        row['cluster_id'],
                        row['category']
                    ))
                except Exception as e:
                    print(f"Failed to generate embedding for signal ID {row['id']}: {e}")
                    
            if not insert_data:
                print("No valid signals to insert after filtering out empty contents.")
                return

            # 3 & 4. Batch Insertion with ON CONFLICT (Idempotency)
            insert_query = """
                INSERT INTO signal_embeddings (id, embedding, content, competitor_id, cluster_id, category)
                VALUES (%s, %s::vector, %s, %s, %s, %s)
                ON CONFLICT (id) DO NOTHING;
            """
            
            execute_batch(cur, insert_query, insert_data)
            conn.commit()
            
            print(f"Processed {len(insert_data)} signals successfully.")
            
    except psycopg2.Error as db_err:
        print(f"Database connection or execution failed: {db_err}")
        if conn is not None:
            conn.rollback()
    except Exception as e:
        print(f"Critical pipeline error: {e}")
    finally:
        if conn is not None:
            conn.close()

if __name__ == "__main__":
    # Provides CLI entry point compatibility for local tests or node-cron hooks:
    # python embedding_pipeline.py
    run_embedding_pipeline()
