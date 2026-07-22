# Trackr: Open-Source Computer Vision Platform

Trackr is an open-source computer vision platform designed for real-time and offline video object detection, tracking, and spatial analytics. Using YOLOv8 and ByteTrack, it processes video streams to compute unique object counts, speed estimation, dwell times, and activity heatmaps. It features a distributed FastAPI backend, a Celery task worker, and a Streamlit-based web dashboard.

---

## 🏗 Architecture Summary

Trackr is composed of modular services designed for horizontal scalability and fast inference:

- **Streamlit Frontend**: A rich, responsive web dashboard (served on port `8501`) that allows users to manage projects/workspaces, upload videos, configure streams, view system performance, and watch processed feeds in real time over WebSockets.
- **FastAPI Backend**: The central REST and WebSocket API Gateway (served on port `8000`), handling authentication, project data containment, stream states, and batch processing requests.
- **Celery Worker**: An asynchronous worker executing heavy computer vision pipelines (detection, tracking, and logging) in the background.
- **Redis**: The message broker connecting the FastAPI backend with the Celery worker, and caching real-time stream status.
- **PostgreSQL**: Relational database storing users, projects, job logs, and stream configurations.
- **Inference Pipeline**: Integrates YOLOv8 (via ONNX Runtime or PyTorch) for detection, ByteTrack (via the `supervision` library) for robust tracking, and OpenCV for video rendering and I/O.

### Data Flow

```
   [ Streamlit UI ] <============== (WebSockets) =============+
          |                                                   |
          | (REST)                                            |
          v                                                   v
   [ FastAPI Backend ] ---> [ Redis Broker ] ---> [ Celery Worker (Inference) ]
          |                                                   |
          +-----------> [ PostgreSQL DB ] <-------------------+
```

---

## 💻 Prerequisites

- **Docker Desktop**: Required to orchestrate containerized services.
- **Python 3.11**: Pinned target version for development, testing, and CI.
- **PowerShell / Terminal**: Used to execute build and development scripts.

---

## 🛠 Setup Instructions

### 1. Clone the Repository & Configure Pre-commit
Clone the codebase and install pre-commit hooks to automatically check code formatting:
```bash
git clone https://github.com/trackr/trackr.git
cd trackr
pre-commit install
```

### 2. Configure Environment Variables
Navigate to the source directory and copy the template configuration file:
```bash
cd object-tracker
cp .env.example .env
```

Open `.env` and fill in the required keys. Below are the variables utilized by the system (see `config/settings.py` for defaults):

| Variable | Description | Example / Default |
| :--- | :--- | :--- |
| `DATABASE_URL` | PostgreSQL connection URL | `postgresql+asyncpg://trackr_user:trackr_password@db/trackr_db` |
| `REDIS_URL` | Redis URL | `redis://redis:6379/0` |
| `CELERY_BROKER_URL` | Celery broker URL | `redis://redis:6379/0` |
| `EXECUTION_BACKEND` | Background job engine | `celery` |
| `YOLO_MODEL_PATH` | Weights filename | `yolov8n.pt` |
| `CONFIDENCE_THRESHOLD` | Detection confidence | `0.3` |
| `HARDWARE_ACCELERATION` | Inference hardware target | `auto` (or `cpu`, `cuda`) |
| `TEMP_DIR` | Upload processing folder | `data/temp` |
| `OUTPUT_DIR` | Target folder for outputs | `outputs/api` |
| `LOG_DIR` | Core logging output directory | `outputs` |
| `LOG_LEVEL` | Logging verbosity | `INFO` |
| `LOG_FORMAT` | Log payload pattern | `json` (or `text`) |
| `SECRET_KEY` | JWT signing secret | `your-super-secret-development-key` |
| `API_BASE_URL` | Streamlit -> Backend URL | `http://localhost:8000/api/v1` |
| `SYS_API_BASE_URL` | Streamlit -> Health Check | `http://localhost:8000/api/v1/system` |

### 3. Spin Up Services in Docker
Start all defined services (database, redis, backend, worker, and frontend):
```bash
docker compose up -d
```

### 4. Run Alembic Database Migrations
Apply the initial migration schema inside the running backend container:
```bash
docker compose exec backend alembic upgrade head
```

### 5. Access the Platform
- **Streamlit Web UI**: [http://localhost:8501](http://localhost:8501)
- **FastAPI API Swagger Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 🎥 Usage Walkthrough

### Flow A: Offline Batch Video Processing
1. Open the Streamlit dashboard and log in / register.
2. Under the **Workspaces** section in the sidebar, select an existing workspace or input a name in **New Project** and click **Create**.
3. In the main page, navigate to the **Offline Batch Processing** tab.
4. Upload an `.mp4` video using the file uploader and click **Process Video**.
5. Once queued, track live execution status (progress percentage, current speed in FPS, ETA).
6. Upon completion, expand the job in the **Job History** list to watch the processed video overlay, analyze the spatial density heatmap, view classification charts, and download the CSV telemetry report.

### Flow B: Real-Time Stream Monitoring
1. Under the **Live Streaming** tab, expand the **Add New Stream** section.
2. In the **Stream Source** field, input an RTSP source stream URL, a local video path, or `"0"` (for local webcam testing natively). Click **Add Stream**.
3. Locate the stream in the list and click **▶️ Start** to initialize the pipeline.
4. Once active (`PLAYING`), click **👀 View Live Feed** to open a real-time canvas streaming inference outputs over WebSockets.

---

## ⚠️ Known Limitations (Windows / WSL2)

On Windows or macOS running Docker Desktop, the underlying VM **cannot access local physical hardware (USB webcams)** like the integrated laptop camera (source `"0"`).
- **RTSP and Video Files**: You can fully test streaming in Docker Compose using RTSP streams or raw video files.
- **Native Webcam Workaround**: If you need to test live webcam tracking natively, run PostgreSQL and Redis in Docker, and start the FastAPI, Celery, and Streamlit components natively on Windows (which accesses the camera via DirectShow/MSMF) by running the hybrid script:
  ```powershell
  .\run_dev.ps1
  ```

---

## 🧪 Local Testing & CI Quality Checks

Before committing and pushing code changes, ensure all tests and quality checks pass. Run these commands sequentially inside the `object-tracker` directory (matching the exact `.github/workflows/ci.yml` pipeline flow):

### 1. Check Formatting (Black)
```bash
black --check .
```
*(To apply formatting changes directly, run `black .`)*

### 2. Linting Checks (Ruff)
```bash
ruff check .
```

### 3. Static Type Checking (MyPy)
```bash
mypy .
```

### 4. Run the Pytest Suite
```bash
pytest tests/ --cov=. --cov-report=xml
```

---

## 🤝 Contributing

We welcome additions and optimization PRs. To maintain the project's health:
1. **Run Local Checks**: Ensure `black`, `ruff`, `mypy`, and `pytest` pass cleanly before submitting a PR.
2. **Pre-commit Hooks**: Keep pre-commit active to catch style changes before commits are generated.
3. **Scoped Changes**: Keep code edits tightly scoped to the specific feature or bug fix. Avoid mixing unrelated modifications or restructuring modules to prevent regressions in other parts of the video processing pipeline.
