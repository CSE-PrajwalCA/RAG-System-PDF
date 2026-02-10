# CI/CD & AWS Deployment Guide

This guide explains how to set up a continuous integration/deployment pipeline using GitHub Actions and deploy the containerized RAG system to AWS EC2.

## 1. Prerequisites
- **GitHub Repository**: Push this code to a new repo.
- **Docker Hub Account**: Create repositories for `rag-backend`, `rag-frontend`, and `shakti-db` (custom image).
- **AWS Account**: Access to launch EC2 instances.

---

## 2. Verify Production Build Locally (Before Pushing)
Before pushing to GitHub, verify that your Docker build works locally (simulating the production environment).

1.  **Stop Local Dev Servers**:
    ```powershell
    # Stop any running python/node processes
    # Stop existing containers
    docker-compose down
    ```

2.  **Build and Run with Docker**:
    ```powershell
    # Rebuild everything to ensure latest code is used
    docker-compose up -d --build
    ```

3.  **Test**:
    - Frontend: `http://localhost:3000` (This is now served by Nginx in Docker!)
    - Backend: `http://localhost:8000/docs`
    - **Note**: If this works, your code is ready for CI/CD.

---

## 3. GitHub Actions Workflow (CI/CD)
Create a file `.github/workflows/deploy.yml` in your repository.

```yaml
name: Build and Push Docker Images

on:
  push:
    branches: [ "main" ]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v3

      - name: Login to Docker Hub
        uses: docker/login-action@v2
        with:
          username: ${{ secrets.DOCKERHUB_USERNAME }}
          password: ${{ secrets.DOCKERHUB_TOKEN }}

      - name: Build and Push Backend
        uses: docker/build-push-action@v4
        with:
          context: ./backend
          push: true
          tags: ${{ secrets.DOCKERHUB_USERNAME }}/rag-backend:latest

      - name: Build and Push Frontend
        uses: docker/build-push-action@v4
        with:
          context: ./frontend
          push: true
          tags: ${{ secrets.DOCKERHUB_USERNAME }}/rag-frontend:latest
```

**Secrets**: Go to GitHub Repo -> Settings -> Secrets and add `DOCKERHUB_USERNAME` and `DOCKERHUB_TOKEN`.

---

## 3. AWS EC2 Deployment

### A. Launch Instance
1.  **OS**: Ubuntu Server 22.04 LTS (or Amazon Linux 2023).
2.  **Instance Type**: `t3.large` or `t3.xlarge` (Need 8GB+ RAM for LLM).
3.  **Storage**: 30GB+ GP3 Root Volume.
4.  **Security Group**:
    - Allow SSH (22) from My IP.
    - Allow HTTP (80) or Custom TCP (3000) for Frontend.
    - Allow Custom TCP (8000) for Backend API (if public access needed).

### B. Install Docker on EC2
SSH into your instance and run:

```bash
# Update and Install Docker
sudo apt-get update
sudo apt-get install -y docker.io docker-compose

# Start Docker
sudo systemctl start docker
sudo systemctl enable docker

# Add user to docker group (avoid sudo)
sudo usermod -aG docker $USER
newgrp docker
```

### C. Deploy Application
1.  **Copy `docker-compose.yml`**:
    You can `scp` the file or just create it on the server:
    ```bash
    nano docker-compose.yml
    # Paste the content of your local docker-compose.yml
    ```

2.  **Update Image References**:
    Edit the `docker-compose.yml` on the server to point to your Docker Hub images instead of `build: .`.
    
    *Example Change:*
    ```yaml
    backend:
      image: <your-dockerhub-user>/rag-backend:latest
      # build: ./backend  <-- Remove this
    
    frontend:
      image: <your-dockerhub-user>/rag-frontend:latest
      # build: ./frontend <-- Remove this
    ```

3.  **Start the System**:
    ```bash
    docker-compose up -d
    ```

### D. Verify
- Run `docker-compose ps` to see all services running.
- Access the app at `http://<EC2-Public-IP>:3000`.

---
## 4. Maintenance / Updates
To update the app after pushing new code:
1.  SSH into EC2.
2.  Run:
    ```bash
    docker-compose pull
    docker-compose up -d
    ```
