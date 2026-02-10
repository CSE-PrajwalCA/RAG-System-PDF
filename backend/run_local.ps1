# Set environment variables for local development
$env:DB_HOST = "localhost"
$env:DB_PORT = "15234"
$env:DB_USER = "postgres"
$env:DB_PASSWORD = "postgres"
$env:META_DB = "rag_meta"
$env:VECTOR_DB = "rag_vector"
$env:OLLAMA_BASE_URL = "http://localhost:11434"

# Print configuration for verification
Write-Host "Starting Backend with Local Configuration:" -ForegroundColor Green
Write-Host "DB_HOST: $env:DB_HOST"
Write-Host "DB_PORT: $env:DB_PORT"
Write-Host "OLLAMA: $env:OLLAMA_BASE_URL"

# Activate venv if exists
if (Test-Path "..\venv\Scripts\Activate.ps1") {
    . ..\venv\Scripts\Activate.ps1
}

# Run Uvicorn
uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 --reload
