# Python SDK Guide — Trackr v1.0

The official `trackr-sdk` package allows developers to interact with the Trackr API server programmatically.

---

## 1. Installation
Install the SDK via pip:
```bash
pip install trackr-sdk
```

---

## 2. API Connection

To initialize the client, you require the URL of the API server and a JWT access token:

```python
from trackr_sdk import TrackrClient

# Connect to the API
client = TrackrClient(base_url="http://localhost:8000", token="your_jwt_access_token")
```

---

## 3. Submitting Batch Video Jobs

```python
# Upload and queue a video for tracking
job = client.submit_job(
    video_path="intersection.mp4",
    project_id="c0a87c75-4f91-4860-ae7d-2afa1cc0ce32"
)
print(f"Job created with ID: {job.id}")

# Wait until completion (polls status endpoint automatically)
results = client.wait_for_job(job.id, timeout=300)
print("Processing Completed!")
print(f"Total Unique Objects: {results['traffic_stats']['total_unique_objects']}")
```

---

## 4. Retrieving Outputs

After the video processing job is completed, you can fetch its telemetry outputs:

```python
# 1. Download analytics JSON
analytics = client.get_job_analytics(job.id)
print(f"Class distributions: {analytics['class_distribution']}")

# 2. Download annotated video file
client.download_video(job.id, output_path="outputs/annotated_intersection.mp4")

# 3. Download heatmap PNG
client.download_heatmap(job.id, output_path="outputs/intersection_heatmap.png")

# 4. Download tracking CSV report
client.download_report(job.id, output_path="outputs/intersection_coords.csv")
```
