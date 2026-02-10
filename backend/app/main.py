from fastapi import FastAPI, UploadFile, File, HTTPException, status
from fastapi.concurrency import run_in_threadpool
from pypdf import PdfReader
import io
import uuid
import logging
from contextlib import asynccontextmanager

from app.chunking import chunk_text
from app.embeddings import embed_texts
from app.retrieval import retrieve_similar_chunks
from app.prompt import build_rag_prompt
from app.ollama_client import generate_answer
from app.db import get_meta_conn, get_vector_conn
from app.db_init import initialize_db

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize DB
    try:
        logger.info("Initializing database...")
        # Run DB init in a thread to avoid blocking if it takes time (though it uses sleep internally)
        await run_in_threadpool(initialize_db)
        logger.info("Database initialized successfully.")
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        # In production, you might want to crash here if DB is critical
    yield
    # Shutdown logic if needed

app = FastAPI(title="RAG Backend", lifespan=lifespan)

@app.get("/health")
def health():
    return {"status": "ok"}

def _process_pdf_content(file_content: bytes) -> str:
    """
    Extract text from PDF bytes. Blocked CPU operation.
    """
    try:
        reader = PdfReader(io.BytesIO(file_content))
        full_text = ""
        for page in reader.pages:
            text = page.extract_text()
            if text:
                full_text += text + "\n"
        return full_text
    except Exception as e:
        logger.error(f"Error reading PDF: {e}")
        raise ValueError("Invalid PDF file")

@app.post("/upload-pdf")
async def upload_pdf(file: UploadFile = File(...)):
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    logger.info(f"Receiving file: {file.filename}")
    
    try:
        # 1. Read file (Async I/O)
        pdf_bytes = await file.read()
        
        # 2. Extract Text (CPU bound -> Threadpool)
        full_text = await run_in_threadpool(_process_pdf_content, pdf_bytes)
        
        if not full_text.strip():
             raise HTTPException(status_code=400, detail="PDF contains no extractable text.")

        # 3. Chunk Text (CPU bound -> Threadpool)
        chunks = await run_in_threadpool(chunk_text, full_text)
        
        # 4. Generate Embeddings (CPU bound -> Threadpool)
        texts = [c["text"] for c in chunks]
        embeddings = await run_in_threadpool(embed_texts, texts)

        # 5. DB Operations (I/O bound but blocking psycopg2 -> Threadpool recommended or just standard def if we werent in async def)
        # Since we are in async def, direct blocking calls block the loop.
        # We'll use run_in_threadpool for the transaction block to be safe.
        
        def save_to_db():
            meta_conn = get_meta_conn()
            vector_conn = get_vector_conn()
            try:
                meta_cur = meta_conn.cursor()
                vector_cur = vector_conn.cursor()
                
                for idx, chunk in enumerate(chunks):
                    chunk_id = str(uuid.uuid4())
                    # Convert numpy float32 to python float for JSON serialization if needed, 
                    # but psycopg2 handles lists for array/vector input usually.
                    embedding_list = embeddings[idx].tolist() 
                    
                    meta_cur.execute(
                        """
                        INSERT INTO document_chunks (chunk_id, document_name, chunk_index, content)
                        VALUES (%s, %s, %s, %s)
                        """,
                        (chunk_id, file.filename, idx, chunk["text"])
                    )
                    
                    vector_cur.execute(
                        """
                        INSERT INTO chunk_vectors (chunk_id, embedding)
                        VALUES (%s, %s)
                        """,
                        (chunk_id, embedding_list)
                    )
                
                meta_conn.commit()
                vector_conn.commit()
                
                meta_cur.close()
                vector_cur.close()
            except Exception as e:
                meta_conn.rollback()
                vector_conn.rollback()
                logger.error(f"Database transaction failed: {e}")
                raise e
            finally:
                meta_conn.close()
                vector_conn.close()

        await run_in_threadpool(save_to_db)
        
        logger.info(f"Processed {file.filename} with {len(chunks)} chunks.")
        
        return {
            "filename": file.filename,
            "num_chunks": len(chunks),
            "status": "success"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/query")
async def query_rag(question: str):
    if not question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    logger.info(f"Processing query: {question}")
    
    try:
        # 1. Retrieve chunks (CPU/DB bound)
        # retrieve_similar_chunks handles DB connection internally and doing embedding
        chunk_ids = await run_in_threadpool(retrieve_similar_chunks, question, 5)
        
        if not chunk_ids:
             return {
                "question": question,
                "answer": "Not found in the document.",
                "sources": []
            }

        # 2. Fetch content (DB bound)
        def fetch_content():
            meta_conn = get_meta_conn()
            try:
                with meta_conn.cursor() as cur:
                    # ANY(%s) works with list in psycopg2
                    cur.execute(
                        """
                        SELECT content 
                        FROM document_chunks 
                        WHERE chunk_id::text = ANY(%s::text[])
                        """,
                        (chunk_ids,)
                    )
                    return [row[0] for row in cur.fetchall()]
            finally:
                meta_conn.close()

        context_chunks = await run_in_threadpool(fetch_content)

        # 3. Build Prompt (CPU)
        prompt = build_rag_prompt(question, context_chunks)

        # 4. Generate Answer (Network/Ollama bound)
        # generate_answer uses requests (blocking), so run in threadpool
        answer = await run_in_threadpool(generate_answer, prompt)

        return {
            "question": question,
            "answer": answer,
            "sources": context_chunks
        }

    except Exception as e:
        logger.error(f"Query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
