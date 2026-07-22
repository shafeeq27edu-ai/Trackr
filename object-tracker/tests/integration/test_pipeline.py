import os
import time

import pytest
from fastapi.testclient import TestClient


def test_full_video_pipeline(client: TestClient):
    """
    E2E Integration Test: Uploads a real sample video, polls for completion,
    and validates the generated outputs (Analytics JSON, Report CSV, Heatmap PNG).
    """
    # 1. Upload Video
    sample_path = "data/sample_videos/sample.mp4"
    if not os.path.exists(sample_path):
        pytest.skip("Sample video not found. Skipping E2E test.")

    with open(sample_path, "rb") as f:
        response = client.post(
            "/api/v1/jobs/upload", files={"file": ("sample.mp4", f, "video/mp4")}
        )

    assert response.status_code == 200
    job_id = response.json()["job_id"]

    # 2. Poll for Completion (Max 120 seconds to prevent infinite hang)
    max_retries = 120
    retries = 0
    job = None

    while retries < max_retries:
        res = client.get(f"/api/v1/jobs/{job_id}")
        assert res.status_code == 200
        job = res.json()

        status = job.get("status")
        if status == "COMPLETED":
            break
        elif status == "FAILED":
            pytest.fail(f"Background job failed: {job.get('error')}")

        time.sleep(1)
        retries += 1

    if retries == max_retries:
        pytest.fail("Job timed out before completion.")

    assert job is not None
    assert "analytics" in job

    # 3. Validate Endpoints
    # Analytics
    analytics_res = client.get(f"/api/v1/jobs/{job_id}/analytics")
    assert analytics_res.status_code == 200
    summary = analytics_res.json()["analytics"]
    assert "traffic_stats" in summary
    assert "video_stats" in summary

    # Heatmap
    heatmap_res = client.get(f"/api/v1/jobs/{job_id}/heatmap")
    assert heatmap_res.status_code == 200
    assert heatmap_res.headers["content-type"] == "image/png"

    # Report (CSV)
    report_res = client.get(f"/api/v1/jobs/{job_id}/report")
    assert report_res.status_code == 200
    assert report_res.headers["content-type"].startswith("text/csv")
