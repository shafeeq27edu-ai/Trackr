import pytest
import os
from unittest.mock import patch
from fastapi.testclient import TestClient

def test_upload_invalid_format(client: TestClient):
    # Upload a .txt file
    files = {"file": ("test.txt", b"dummy content", "text/plain")}
    response = client.post("/api/v1/jobs/upload", files=files)
    
    assert response.status_code == 400
    assert "Unsupported file format" in response.json()["detail"]

@patch("api.v1.jobs.BackgroundTasks.add_task")
def test_upload_valid_video(mock_add_task, client: TestClient):
    files = {"file": ("test.mp4", b"dummy video bytes", "video/mp4")}
    response = client.post("/api/v1/jobs/upload", files=files)
    
    assert response.status_code == 200
    data = response.json()
    assert "job_id" in data
    assert data["status"] == "initializing"
    
    # Ensure the background task was dispatched
    mock_add_task.assert_called_once()

def test_get_job_status_not_found(client: TestClient):
    response = client.get("/api/v1/jobs/nonexistent-id")
    assert response.status_code == 404

def test_get_heatmap_not_ready(client: TestClient):
    # We first create a job so it's in the system but not completed
    files = {"file": ("test.mp4", b"dummy video bytes", "video/mp4")}
    upload_res = client.post("/api/v1/jobs/upload", files=files)
    job_id = upload_res.json()["job_id"]
    
    # Attempting to get heatmap should fail because it's not completed
    response = client.get(f"/api/v1/jobs/{job_id}/heatmap")
    assert response.status_code == 404
    assert "not available yet" in response.json()["detail"]
