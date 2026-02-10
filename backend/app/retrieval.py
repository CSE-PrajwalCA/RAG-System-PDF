import numpy as np
import psycopg2
from app.embeddings import embed_texts
from app.db import get_vector_conn


def retrieve_similar_chunks(query: str, top_k: int = 5):
    """
    Retrieve similar chunks using pgvector's native efficient search.
    """
    # 1. Generate embedding for the query
    query_vec = embed_texts([query])[0]
    # Convert to list and then string for SQL adaptation
    # Convert to list and then string for SQL adaptation
    # pgvector requires '[1,2,3]' format for casting, but psycopg2 default list adapter uses '{1,2,3}'
    # Remove spaces to ensure compatibility
    query_embedding = str(query_vec.tolist()).replace(' ', '')

    conn = get_vector_conn()
    try:
        with conn.cursor() as cur:
            # 2. Use pgvector's cosine distance operator (<=>)
            # The operator <=> returns the cosine distance (0 to 2).
            # Lower distance = Higher similarity.
            # Manual query construction to avoid psycopg2 casting issues with pgvector
            # query_embedding is a string '[x, y, z]' derived from floats, so it is safe.
            cur.execute(
                f"""
                SELECT chunk_id
                FROM chunk_vectors
                ORDER BY embedding <=> '{query_embedding}'::vector
                LIMIT %s
                """,
                (top_k,)
            )
            rows = cur.fetchall()
            
            # Return just the list of chunk_ids
            return [row[0] for row in rows]
            
    except Exception as e:
        print(f"Error during vector retrieval: {e}")
        return []
    finally:
        conn.close()
