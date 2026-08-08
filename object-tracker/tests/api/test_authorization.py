import pytest

@pytest.fixture
def users(auth_client):
    # User A
    userA = {"email": "usera@example.com", "password": "Password123!", "username": "usera"}
    auth_client.post("/api/v1/auth/register", json=userA)
    tokenA = auth_client.post("/api/v1/auth/login", data={"username": userA["email"], "password": userA["password"]}).json()["access_token"]
    
    # User B
    userB = {"email": "userb@example.com", "password": "Password123!", "username": "userb"}
    auth_client.post("/api/v1/auth/register", json=userB)
    tokenB = auth_client.post("/api/v1/auth/login", data={"username": userB["email"], "password": userB["password"]}).json()["access_token"]
    
    return {"A": tokenA, "B": tokenB}


def test_idor_job_access(auth_client, users):
    tokenA = users["A"]
    tokenB = users["B"]
    
    # User A creates a job (mocking the upload since DB is handled)
    res_upload = auth_client.post("/api/v1/jobs/upload", files={"file": ("test.mp4", b"dummy video bytes", "video/mp4")}, headers={"Authorization": f"Bearer {tokenA}"})
    assert res_upload.status_code == 200
    job_id = res_upload.json()["job_id"]
    
    # User B tries to access it
    res_b = auth_client.get(f"/api/v1/jobs/{job_id}", headers={"Authorization": f"Bearer {tokenB}"})
    assert res_b.status_code in [403, 404]

    # User A CAN access their own job
    res_a = auth_client.get(f"/api/v1/jobs/{job_id}", headers={"Authorization": f"Bearer {tokenA}"})
    assert res_a.status_code == 200


def test_idor_project_access(auth_client, users):
    tokenA = users["A"]
    tokenB = users["B"]
    
    res_proj = auth_client.post("/api/v1/projects/", json={"name": "Project A"}, headers={"Authorization": f"Bearer {tokenA}"})
    assert res_proj.status_code == 200
    project_id = res_proj.json()["id"]
    
    # User B tries to delete it
    res_b = auth_client.delete(f"/api/v1/projects/{project_id}", headers={"Authorization": f"Bearer {tokenB}"})
    assert res_b.status_code in [403, 404]

    # User A CAN delete their own project
    res_a = auth_client.delete(f"/api/v1/projects/{project_id}", headers={"Authorization": f"Bearer {tokenA}"})
    assert res_a.status_code == 200


def test_idor_stream_access(auth_client, users):
    tokenA = users["A"]
    tokenB = users["B"]
    
    res_stream = auth_client.post("/api/v1/streams", json={"source": "rtsp://test"}, headers={"Authorization": f"Bearer {tokenA}"})
    assert res_stream.status_code == 200
    stream_id = res_stream.json()["id"]
    
    # User B tries to access it
    res_b = auth_client.get(f"/api/v1/streams/{stream_id}", headers={"Authorization": f"Bearer {tokenB}"})
    assert res_b.status_code in [403, 404]

    # User A CAN access their own stream
    res_a = auth_client.get(f"/api/v1/streams/{stream_id}", headers={"Authorization": f"Bearer {tokenA}"})
    assert res_a.status_code == 200
