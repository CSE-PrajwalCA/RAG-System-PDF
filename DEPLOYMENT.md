# Enterprise RAG System - Deployment Guide

This guide details the deployment of the production-grade RAG system. The system works out-of-the-box on any machine with Docker and Docker Compose (specifically tested on AWS EC2).

## Architecture Overview

The system consists of 5 coordinated containers:
1.  **shakti-db** (Port `15234`): The persistent data layer using PostgreSQL 17.4. Stores document metadata, chunks, and vector embeddings (via `pgvector`).
2.  **rag-backend** (Port `8000`): FastAPI application handling ingestion, chunking, embedding, and retrieval.
3.  **rag-frontend** (Port `3000`): React + Nginx UI for uploading PDFs and chatting.
4.  **ollama** (Port `11434`): Local LLM inference engine.
5.  **ollama-init**: Ephemeral utility container that ensures the `qwen:1.5b` model is pulled and ready before the backend starts.

## Prerequisites

- **Docker**: Version 20.10+
- **Docker Compose**: Version 2.20+ (supports `service_completed_successfully`)
- **Hardware**: Minimum 8GB RAM recommended (for LLM and Vector DB), 4 vCPUs.
- **Disk**: At least 20GB free space (for Docker images and vector data).

## Deployment Steps

1.  **Clone the Repository**
    ```bash
    git clone <repository_url>
    cd rag-system
    ```

2.  **Configuration (Optional)**
    - Check `.env` or `docker-compose.yml` if you need to change ports.
    - Default configuration binds to `0.0.0.0` for all services.

3.  **Start the System**
    Run the following command to build images and start services in detached mode:
    ```bash
    docker-compose up --build -d
    ```

4.  **Wait for Initialization**
    - The `ollama-init` container will automatically pull the `qwen:1.5b` model. This may take a few minutes depending on internet speed.
    - The `shakti-db` container will perform its 10-step initialization process (approx. 5-10 seconds).
    - The `rag-backend` will start only after the database is healthy and the model is pulled.

5.  **Verify Status**
    Check that all containers are running:
    ```bash
    docker-compose ps
    ```
    You should see:
    - `shakti-db`: Up (healthy)
    - `ollama`: Up (healthy)
    - `ollama-init`: Exited (0) (This is normal and expected)
    - `rag-backend`: Up
    - `rag-frontend`: Up

## Operations & Usage

- **Access the UI**: Navigate to `http://<your-server-ip>:3000`
- **Upload API**: `POST http://<your-server-ip>:8000/upload-pdf`
- **Query API**: `POST http://<your-server-ip>:8000/query`

### Monitoring
- **Backend Logs**:
    ```bash
    docker logs -f rag-backend
    ```
- **DB Logs**:
    ```bash
    docker logs -f shakti-db
    ```

### Data Persistence
- Database data is persisted in the `shakti-db-data` Docker volume.
- LLM models are persisted in the `ollama-data` Docker volume.
- Restarting containers will **not** lose data.

## Troubleshooting

**Issue: Backend keeps restarting**
- Check logs: `docker logs rag-backend`
- Likely cause: Waiting for `ollama-init` to finish pulling the model. Be patient on first launch.

**Issue: Database encoding errors**
- Run the verification command:
    ```bash
    docker exec shakti-db bash -c "export PGPORT=15234 && psql -U postgres -c 'SHOW server_encoding;'"
    ```
- Should return `UTF8`.

**Issue: Vector Search is slow**
- Ensure `hnsw` index is created. The backend attempts to create it on startup via `db_init.py`.
- Check DB resource usage: `docker stats shakti-db`
