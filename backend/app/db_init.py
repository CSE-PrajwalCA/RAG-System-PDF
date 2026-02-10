import os
import time
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# Re-use config from db.py structure but keep it independent for init script
DB_HOST = os.getenv("DB_HOST", "shakti-db")
DB_PORT = int(os.getenv("DB_PORT", 15234))
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")
META_DB = os.getenv("META_DB", "rag_meta")
VECTOR_DB = os.getenv("VECTOR_DB", "rag_vector")

def get_admin_conn():
    """
    Connect to the default 'postgres' database to create other databases.
    """
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        dbname="postgres"
    )
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    return conn

def wait_for_db():
    retries = 30
    while retries > 0:
        try:
            conn = get_admin_conn()
            conn.close()
            print("Successfully connected to ShaktiDB.")
            return
        except psycopg2.OperationalError as e:
            print(f"Waiting for database... ({retries} retries left) - {e}")
            time.sleep(2)
            retries -= 1
    raise Exception("Could not connect to database after multiple retries.")

def create_database_if_not_exists(cursor, db_name):
    cursor.execute(f"SELECT 1 FROM pg_catalog.pg_database WHERE datname = '{db_name}'")
    exists = cursor.fetchone()
    if not exists:
        print(f"Creating database: {db_name}")
        cursor.execute(f"CREATE DATABASE {db_name} ENCODING 'UTF8'")
    else:
        print(f"Database {db_name} already exists.")

def init_meta_db():
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        dbname=META_DB
    )
    conn.autocommit = True
    with conn.cursor() as cur:
        # Create document_chunks table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS document_chunks (
                chunk_id UUID PRIMARY KEY,
                document_name TEXT NOT NULL,
                chunk_index INT NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        # Create chat_history table (optional but good for production)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS chat_history (
                id SERIAL PRIMARY KEY,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                user_question TEXT NOT NULL,
                assistant_answer TEXT NOT NULL,
                sources TEXT
            );
        """)
    conn.close()
    print("Initialized meta database schema.")

def init_vector_db():
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        dbname=VECTOR_DB
    )
    conn.autocommit = True
    with conn.cursor() as cur:
        # Enable pgvector extension
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        
        # Create chunk_vectors table
        # Using 384 dimensions for all-MiniLM-L6-v2
        cur.execute("""
            CREATE TABLE IF NOT EXISTS chunk_vectors (
                chunk_id UUID PRIMARY KEY,
                embedding vector(384)
            );
        """)
        
        # Create hnsw index for faster search
        # We wrap this in a try-except block because creating the index on an empty table is fine,
        # but sometimes standard SQL behavior varies on "IF NOT EXISTS" for indexes with specific opclasses.
        # "CREATE INDEX IF NOT EXISTS" is standard in recent PG.
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_chunk_vectors_embedding 
            ON chunk_vectors 
            USING hnsw (embedding vector_cosine_ops);
        """)
        
    conn.close()
    print("Initialized vector database schema.")

def initialize_db():
    print("Starting Database Initialization...")
    wait_for_db()
    
    # 1. Create Databases
    admin_conn = get_admin_conn()
    with admin_conn.cursor() as cur:
        create_database_if_not_exists(cur, META_DB)
        create_database_if_not_exists(cur, VECTOR_DB)
    admin_conn.close()
    
    # 2. Init Schemas
    init_meta_db()
    init_vector_db()
    print("Database Initialization Complete.")

if __name__ == "__main__":
    initialize_db()
