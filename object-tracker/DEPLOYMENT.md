# Trackr Deployment Guide

This guide explains how to deploy Trackr in a production environment using Docker and standard PaaS providers.

## Prerequisites
- Docker & Docker Compose
- Environment file (`.env`)

## Option 1: Docker Compose (Self-Hosted / VPS)

The easiest way to run the entire Trackr stack is via Docker Compose.

1. Clone the repository.
2. Copy the `.env.example` to `.env` and fill in your secrets (especially `SECRET_KEY`).
3. Build and start the stack:
   ```bash
   docker compose up --build -d
   ```
4. Access the API at `http://localhost:8000` and Streamlit at `http://localhost:8501`.

## Option 2: Render / Railway (PaaS)

Since Trackr consists of two services (Backend and Frontend), you can deploy them as separate Docker services on Render or Railway.

### Backend Service (FastAPI)
- **Environment**: Docker
- **Dockerfile Path**: `backend.Dockerfile`
- **Build Command**: Auto-detected by Dockerfile
- **Start Command**: Auto-detected by Dockerfile
- **Env Vars**: Set `LOG_FORMAT=json`, `LOG_LEVEL=INFO`, `SECRET_KEY`.
- **Disk**: Attach a persistent disk to `/app/data` (SQLite) and `/app/outputs`.

### Frontend Service (Streamlit)
- **Environment**: Docker
- **Dockerfile Path**: `frontend.Dockerfile`
- **Env Vars**: Set `API_BASE_URL` to the internal URL of your backend service (e.g., `http://backend:8000/api/v1`).

## Monitoring & Observability
- **Health Checks**: Trackr exposes three standard probes for container orchestration:
  - `/api/v1/system/health`: Basic alive ping for load balancers.
  - `/api/v1/system/live`: Container lifecycle liveness check.
  - `/api/v1/system/ready`: Readiness check that verifies active database connection and validates model loading.
- **Docker Compose Health Probe**: Since python base images are slim, construct the compose health check using Python's native `urllib`:
  ```yaml
  test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v1/system/health')"]
  ```
- **Metrics**: A Prometheus metrics endpoint is available at `/metrics`.
- **Logs**: Set `LOG_FORMAT=json` in production to output structured logs compatible with Datadog, ELK, or CloudWatch.

## Production Resource Allocation
- **GPU Acceleration**: If running with CUDA support on NVIDIA hardware, ensure the `nvidia-container-toolkit` is configured and pass resource options to `docker-compose`:
  ```yaml
  deploy:
    resources:
      reservations:
        devices:
          - driver: nvidia
            count: all
            capabilities: [gpu]
  ```
- **Database Locks**: SQLite is used for database persistence. For production deployments with high concurrent writes, ensure `/app/trackr.db` is stored on a persistent volume with standard POSIX lock support (avoid networked mounts like NFS/SMB which degrade SQLite locking performance).
