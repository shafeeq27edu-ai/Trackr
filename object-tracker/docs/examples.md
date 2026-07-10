# Code Examples — Trackr v1.0

This guide highlights example scripts provided in the repository to test and integrate Trackr v1.0.

---

## 1. Running Sample Video Generation

To verify OpenCV frame reading and pipeline components, you can run the mock video generation helper script:

```bash
python object-tracker/get_sample_video.py
```
This generates a sample synthetic video file inside `data/sample_videos/sample.mp4` containing shapes moving across the screen, which can be used to test local tracking loops without downloading real footage.

---

## 2. CLI Run Example

Process a video directly from the command line using:
```bash
python object-tracker/app.py
```
This script initializes:
1. `YoloDetectorPlugin` (using `yolov8n.pt`)
2. `ByteTrackerWrapper` (supervision ByteTrack)
3. `AnalyticsEnginePlugin` (dwell times, CSV logs)

And saves an annotated video to `outputs/videos/output_analytics.mp4`.

---

## 3. Client API upload Example

To upload and monitor a tracking job via HTTP requests using Python's `requests` library:

```python
import requests
import time

token = "your_jwt_access_token"
headers = {"Authorization": f"Bearer {token}"}

# 1. Upload file
with open("data/sample_videos/sample.mp4", "rb") as f:
    res = requests.post(
        "http://localhost:8000/api/v1/jobs/upload",
        files={"file": f},
        data={"project_id": "optional-project-uuid"},
        headers=headers
    )
job_id = res.json()["job_id"]
print(f"Spawning Job: {job_id}")

# 2. Poll for completion
while True:
    status_res = requests.get(f"http://localhost:8000/api/v1/jobs/{job_id}", headers=headers)
    job = status_res.json()
    print(f"Status: {job['status']} | Progress: {job['progress']}%")
    
    if job["status"] in ["COMPLETED", "FAILED"]:
        break
    time.sleep(2)
```
