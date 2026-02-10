# Running the RAG System Locally (Hybrid Mode)

This guide explains how to run the **Frontend** and **Backend** directly on your Windows host (for development/debugging) while keeping the **Database** and **LLM** in Docker.

---

## 1. Start Infrastructure (Docker)
First, ensure the database and LLM services are running. We will stop the backend/frontend containers to avoid port conflicts.

**PowerShell (Admin recommended):**
```powershell
cd c:\Project\rag-system
docker-compose up -d shakti-db ollama ollama-init
docker-compose stop backend frontend
```
*(Wait ~1 minute for `shakti-db` to become healthy and `ollama-init` to finish pulling the model.)*

---

## 2. Run Backend (Local)
Run the FastAPI backend using a Python virtual environment.

**Terminal 1:**
```powershell
cd c:\Project\rag-system

# Create and Activate Venv (if not executing this again)
python -m venv venv
.\venv\Scripts\Activate

# Install Dependencies
pip install -r backend\requirements.txt

# Set Environment Variables for Local Dev
$env:DB_HOST="localhost"
$env:DB_PORT="15234"
$env:DB_USER="postgres"
$env:DB_PASSWORD="postgres"
$env:META_DB="rag_meta"
$env:VECTOR_DB="rag_vector"
$env:OLLAMA_BASE_URL="http://localhost:11434"

# Run Server (Reload on code changes)
uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 --reload
```
*Backend is now running at `http://127.0.0.1:8000`*

---

## 3. Run Frontend (Local)
Run the React frontend using Vite.

**Terminal 2:**
```powershell
cd c:\Project\rag-system\frontend

# Install Dependencies
npm install

# Note: 'vite.config.js' has been updated to proxy to http://localhost:8000 for local dev.

# Start Dev Server
npm run dev
```

*Frontend is now running at `http://localhost:5173` (or similar)*

---

## 4. Verification
1. Open Browser: `http://localhost:5173`
2. Upload a PDF.
3. Check **Terminal 1** (Backend) for logs.
4. Check **Terminal 2** (Frontend) for logs.
