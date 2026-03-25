import os
import psycopg2
from psycopg2.extras import DictCursor
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize the embedding model globally
MODEL_NAME = "all-MiniLM-L6-v2"
_model = None

def get_model():
    """
    Returns the loaded sentence transformer model (singleton).
    """
    global _model
    if _model is None:
        _model = SentenceTransformer(MODEL_NAME)
    return _model

def semantic_search(query: str, top_k: int = 5, cluster_id: str = None, category: str = None) -> dict:
    """
    Perform vector similarity search on stored signal embeddings using pgvector.
    
    Args:
        query (str): The search query.
        top_k (int, optional): The maximum number of results to return. Defaults to 5.
        cluster_id (str, optional): Filter by a specific cluster.
        category (str, optional): Filter by a specific category.
        
    Returns:
        dict: A dictionary containing the original query and the similarity search results.
    """
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        raise ValueError("DATABASE_URL environment variable is missing.")

    # 1. Generate Query Embedding
    transformer = get_model()
    query_embedding = transformer.encode(query).tolist()
    
    # Format the embedding sequence explicitly as a string for pgvector casting
    embedding_str = "[" + ",".join(map(str, query_embedding)) + "]"
    
    # 2 & 3. Vector Similarity Search with filtering logic
    sql = """
        SELECT content, competitor_id, cluster_id, category,
               1 - (embedding <=> %s::vector) AS similarity
        FROM signal_embeddings
    """
    
    params = [embedding_str]
    where_clauses = []
    
    if cluster_id:
        where_clauses.append("cluster_id = %s")
        params.append(cluster_id)
        
    if category:
        where_clauses.append("category = %s")
        params.append(category)
        
    if where_clauses:
        sql += " WHERE " + " AND ".join(where_clauses)
        
    sql += """
        ORDER BY embedding <=> %s::vector
        LIMIT %s;
    """
    
    # Append ORDER BY and LIMIT bind parameters
    params.extend([embedding_str, top_k])

    results = []
    conn = None
    try:
        conn = psycopg2.connect(db_url)
        with conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute(sql, tuple(params))
            rows = cur.fetchall()
            
            for row in rows:
                results.append({
                    "content": row['content'],
                    "similarity": round(float(row['similarity']), 4) if row['similarity'] is not None else 0.0,
                    "cluster_id": row['cluster_id'],
                    "category": row['category'],
                    "competitor_id": row['competitor_id']
                })
    finally:
        if conn is not None:
            conn.close()

    # 4. Return Output Format
    return {
        "query": query,
        "results": results
    }
