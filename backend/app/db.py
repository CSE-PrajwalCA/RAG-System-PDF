import os
import psycopg2

DB_HOST = os.getenv("DB_HOST", "shakti-sql")
DB_PORT = int(os.getenv("DB_PORT", 15234))
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")
META_DB = os.getenv("META_DB", "rag_meta")
VECTOR_DB = os.getenv("VECTOR_DB", "rag_vector")


def get_meta_conn():
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        dbname=META_DB,
    )
    conn.set_client_encoding("UTF8")
    return conn


def get_vector_conn():
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        dbname=VECTOR_DB,
    )
    conn.set_client_encoding("UTF8")
    return conn

