import os
import psycopg2
from psycopg2.extras import DictCursor
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Model config
MODEL_NAME = "all-MiniLM-L6-v2"
_model = None


def get_model():
    """
    Singleton pattern for loading embedding model.
    """
    global _model
    if _model is None:
        _model = SentenceTransformer(MODEL_NAME)
        # Warmup (reduces first-call latency)
        _model.encode("warmup")
    return _model


def semantic_search(query: str, top_k: int = 5, cluster_id: str = None, category: str = None) -> dict:
    """
    Perform semantic search using pgvector cosine similarity.

    Args:
        query (str): User query
        top_k (int): Number of results
        cluster_id (str): Optional filter
        category (str): Optional filter

    Returns:
        dict: Query + ranked results
    """

    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        raise ValueError("DATABASE_URL environment variable is missing.")

    try:
        # 1. Generate embedding
        model = get_model()
        query_embedding = model.encode(query).tolist()
        embedding_str = "[" + ",".join(map(str, query_embedding)) + "]"

        # 2. Build SQL dynamically
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

        params.extend([embedding_str, top_k])

        # 3. Execute query
        results = []
        conn = psycopg2.connect(db_url)

        with conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute(sql, tuple(params))
            rows = cur.fetchall()

            for row in rows:
                results.append({
                    "content": row["content"],
                    "similarity": round(float(row["similarity"]), 4) if row["similarity"] else 0.0,
                    "cluster_id": row["cluster_id"],
                    "category": row["category"],
                    "competitor_id": row["competitor_id"]
                })

        conn.close()

        # 4. Handle empty results
        if not results:
            return {
                "query": query,
                "results": [],
                "message": "No relevant signals found"
            }

        return {
            "query": query,
            "results": results
        }

    except Exception as e:
        return {
            "query": query,
            "results": [],
            "error": str(e)
        }