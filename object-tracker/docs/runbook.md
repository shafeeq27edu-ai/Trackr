# Operational Runbook — Trackr v1.0

This runbook outlines standard operating procedures for deploying, managing, maintaining, and recovering Trackr v1.0 instances in production.

---

## 1. Startup Procedures

Trackr is packaged as a multi-container Docker application containing:
* **Backend API**: FastAPI server running on port `8000`.
* **Frontend Web App**: Streamlit client running on port `8501`.

### 1.1 Running with Docker Compose (Recommended)
1. Verify the `.env` configuration file is populated with production credentials.
2. Execute the following command to build and launch in detached mode:
   ```bash
   docker compose up --build -d
   ```
3. Verify containers are active:
   ```bash
   docker compose ps
   ```

### 1.2 Running Manually (Local Development/Debug)
1. Activate virtual environment:
   ```bash
   source venv/bin/activate  # Linux/macOS
   # or
   .\venv\Scripts\activate   # Windows
   ```
2. Start the Backend API (FastAPI):
   ```bash
   uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
   ```
3. Start the Frontend App (Streamlit) in another terminal:
   ```bash
   streamlit run frontend/app.py --server.port 8501
   ```

---

## 2. Shutdown Procedures

### 2.1 Graceful Docker Shutdown
To shut down running Docker services while retaining persistent volume data:
```bash
docker compose down
```

### 2.2 Cold Shutdown (Clearing Volumes)
To shut down and wipe temporary Docker container volumes (does not delete host mount binds):
```bash
docker compose down -v
```

---

## 3. Logs & Observability

### 3.1 Log File Locations
* **Local Run Logs**: Log outputs default to `stdout`/`stderr` and are appended to `outputs/logs.csv` for tracking telemetry.
* **Docker Logs**: Inspect container logs directly via:
  ```bash
  docker compose logs -f backend
  docker compose logs -f frontend
  ```

### 3.2 Production Structured Logs
In production, set `LOG_FORMAT=json` and `LOG_LEVEL=INFO` in `.env` to emit JSON-formatted logs suitable for aggregators like Datadog, ELK, or AWS CloudWatch.

---

## 4. Health & Ready Verification

Verify system availability using the built-in system endpoints:
* **Liveness Probe**: `GET http://localhost:8000/api/v1/system/health`
  - Returns `200 OK` if the server is responsive.
* **Resource Status**: `GET http://localhost:8000/api/v1/system/resources`
  - Returns current CPU, Memory, and VRAM/GPU utilization.
* **Preloaded Models**: `GET http://localhost:8000/api/v1/system/models`
  - Lists models preloaded in memory.

---

## 5. Common Failures & Recovery

### 5.1 CUDA Out of Memory (OOM)
* **Symptom**: Jobs fail with `RuntimeError: CUDA out of memory` or system logs show GPU memory errors.
* **Cause**: Multiple streams or background workers are consuming GPU capacity, or the model size is too large for the VRAM.
* **Recovery**:
  1. Set `HARDWARE_ACCELERATION=cpu` in `.env` to fall back to CPU execution.
  2. Reduce `max_workers` in `config/settings.py` (or set `MAX_WORKERS` env var) to lower concurrency.
  3. Swap to a smaller model (e.g. `yolov8n.pt` instead of `yolov8x.pt`).

### 5.2 Database Lock (`sqlite3.OperationalError: database is locked`)
* **Symptom**: Requests return `500 Internal Server Error` stating the database is locked.
* **Cause**: SQLite concurrency limit exceeded during heavy database write operations.
* **Recovery**:
  1. Trackr uses `connect_args={"check_same_thread": False}` in SQLite, which allows concurrent reads but sequential writes.
  2. For enterprise deployments experiencing database lock issues, migrate to a PostgreSQL instance by updating the `SQLALCHEMY_DATABASE_URL` settings.

### 5.3 WebSocket Stream Disconnections
* **Symptom**: The live view page in Streamlit repeatedly disconnects or logs WebSocket connection failures.
* **Cause**: Network lag, socket timeouts, or reverse-proxy buffer sizes.
* **Recovery**:
  1. Confirm port `8000` is open and not blocked by a firewall or firewall-like middlebox.
  2. If using Nginx as a reverse proxy, ensure WebSocket support is enabled by configuring:
     ```nginx
     proxy_set_header Upgrade $http_upgrade;
     proxy_set_header Connection "upgrade";
     ```

---

## 6. Upgrade Procedures

To perform zero-downtime or minimal-downtime upgrades of a Trackr instance:
1. Pull the latest release code:
   ```bash
   git pull origin main
   ```
2. Apply database migrations:
   ```bash
   alembic upgrade head
   ```
3. Rebuild and restart the container services:
   ```bash
   docker compose up --build -d
   ```
