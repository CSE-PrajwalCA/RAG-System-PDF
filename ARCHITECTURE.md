# System Architecture & Database Design

## 1. High-Level Architecture
The system follows a microservices architecture orchestrated via Docker Compose:

- **Frontend (`rag-frontend`)**: React application serving the UI.
- **Backend (`rag-backend`)**: FastAPI service handling business logic.
- **Database (`shakti-db`)**: Single PostgreSQL instance running on port `15234`.
- **LLM (`ollama`)**: Local inference engine for the `qwen:1.5b` model.
- **Init Service (`ollama-init`)**: Utilities to ensure model availability.

## 2. Database Structure (`shakti-db`)

The system uses a **Split-Database Pattern** within a single PostgreSQL instance to enforce logical separation of concerns.

### Instance Details
- **Port**: `15234`
- **User**: `postgres`
- **Encoding**: `UTF-8` (Strictly enforced)

### Logical Database 1: `rag_meta`
Stores "Hot" data—document content and metadata.

**Table: `document_chunks`**
| Column | Type | Description |
|--------|------|-------------|
| `chunk_id` | `UUID` (PK) | Unique identifier for the chunk. |
| `document_name` | `TEXT` | Name of the source PDF. |
| `chunk_index` | `INT` | Order of the chunk in the document. |
| `content` | `TEXT` | The actual text content (UTF-8). |
| `created_at` | `TIMESTAMP` | Ingestion timestamp. |

### Logical Database 2: `rag_vector`
Stores "Cold" compressed data—vector embeddings for similarity search.

**Extensions**
- `vector`: Enabled for vector operations.

**Table: `chunk_vectors`**
| Column | Type | Description |
|--------|------|-------------|
| `chunk_id` | `UUID` (PK) | Links back to `rag_meta.document_chunks`. |
| `embedding` | `vector(384)` | 384-dimensional embedding (all-MiniLM-L6-v2). |

**Indexes**
- `idx_chunk_vectors_embedding`: **HNSW (Hierarchical Navigable Small World)** index using `vector_cosine_ops` for O(log n) approximate nearest neighbor search.

## 3. Data Flow

### Ingestion Pipeline (`/upload-pdf`)
1.  **Upload**: User uploads PDF to Backend.
2.  **Extraction**: Backend extracts text validates UTF-8.
3.  **Chunking**: Text is split into overlapping windows (e.g., 1000 chars).
4.  **Embedding**: Chunks are sent to `SentenceTransformer` model to generate vectors.
5.  **Transaction**:
    - Text stored in `rag_meta.document_chunks`.
    - Vectors stored in `rag_vector.chunk_vectors`.
    - **Atomic Commit**: Both or neither are saved.

### Retrieval Pipeline (`/query`)
1.  **Embed Query**: User question is embedded into a 384-dim vector.
2.  **Vector Search**: Backend executes SQL on `rag_vector`:
    ```sql
    SELECT chunk_id FROM chunk_vectors 
    ORDER BY embedding <=> %query_vector LIMIT 5;
    ```
    (Uses HNSW index for speed).
3.  **Hydration**: Backend fetches text content from `rag_meta` using retrieved `chunk_ids`.
4.  **Generation**: Retrieved text + Question sent to Ollama (`qwen:1.5b`) to generate the answer.

## 4. Testing & Verification

### Running Locally
To run the system locally, execute:

```bash
docker-compose up --build
```
*Note: The first run will take time to pull the LLM model.*

### Running Tests
A test script `tests/test_e2e.py` is provided to verify the system without manual intervention.

```bash
# Install test dependencies (local only)
pip install requests psycopg2-binary toml

# Run the test suite
python tests/test_e2e.py
```
