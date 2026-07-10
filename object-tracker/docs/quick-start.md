# Quick Start — Trackr v1.0

Get up and running with Trackr in less than 5 minutes.

---

## 1. Run the Command Line CLI

Trackr provides a simple command-line entry point to test YOLOv8 object detection and ByteTrack tracking.

1. Ensure your virtual environment is active.
2. Place a test video at `data/sample_videos/sample.mp4`.
3. Run the CLI app:
   ```bash
   python object-tracker/app.py
   ```
4. Find the annotated output video containing bounding boxes and tracking IDs at `outputs/videos/output_analytics.mp4`.

---

## 2. Launch the Streamlit Dashboard

Trackr has an advanced Streamlit dashboard that lets you manage projects, upload videos, trace unique object counts, and stream live camera feeds.

1. Start the Backend API server:
   ```bash
   cd object-tracker
   uvicorn api.main:app --host 127.0.0.1 --port 8000
   ```

2. Start the Frontend Streamlit client in another shell:
   ```bash
   cd object-tracker
   streamlit run frontend/app.py --server.port 8501
   ```

3. Open your browser and navigate to `http://localhost:8501`.
4. Register a new user account, login, create a workspace project, and upload a video!

---

## 3. Basic Python SDK Quickstart

You can interact with the Trackr API programmatically using the Python SDK:

```python
from trackr_sdk import TrackrClient

# Connect to the local running instance
client = TrackrClient(base_url="http://localhost:8000", token="your_jwt_token")

# Submit a video file for tracking
job = client.submit_job(video_path="path/to/my_video.mp4", project_id="your-project-uuid")
print(f"Tracking job spawned! ID: {job.id}")

# Wait for completion
results = client.wait_for_job(job.id)
print(f"Unique object count: {results['traffic_stats']['total_unique_objects']}")
```
