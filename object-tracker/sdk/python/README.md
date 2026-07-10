# Trackr Python SDK

Official Python SDK and CLI for the Trackr Computer Vision Platform.

## Installation

```bash
pip install trackr-sdk
```

## Usage

```python
from trackr_sdk import TrackrClient

client = TrackrClient("http://localhost:8000")
client.login("admin", "password")

job = client.submit_job("video.mp4")
print(f"Submitted job {job.id}")
```
