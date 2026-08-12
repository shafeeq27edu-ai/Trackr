import asyncio
import os
os.environ["SECRET_KEY"] = "test-secret-key-that-is-long-enough-and-secure"
from httpx import AsyncClient, ASGITransport
from api.main import app

async def poll_job(client, job_id, name):
    print(f"[{name}] Polling job {job_id}")
    while True:
        res = await client.get(f"/api/v1/jobs/{job_id}")
        if res.status_code != 200:
            print(f"[{name}] Failed to get job status: {res.status_code}")
            return False
            
        job = res.json()
        status = job.get("status")
        progress = job.get("progress", 0)
        
        print(f"[{name}] Status: {status}, Progress: {progress:.1f}%")
        
        if status == "COMPLETED":
            print(f"[{name}] JOB COMPLETED SUCCESSFULLY!")
            return True
        elif status == "FAILED":
            print(f"[{name}] JOB FAILED: {job.get('error')}")
            return False
            
        await asyncio.sleep(1)

async def run_concurrent_jobs():
    # Make sure we bypass auth for this test script by setting test credentials or overriding
    from api.deps import get_current_user
    from db.models import User
    dummy_user = User(id="test-user-id", email="test@example.com", name="Test User")
    app.dependency_overrides[get_current_user] = lambda: dummy_user

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        # We need a sample video file
        sample_path = "data/sample_videos/sample.mp4"
        if not os.path.exists(sample_path):
            print(f"Sample video not found at {sample_path}")
            return

        with open(sample_path, "rb") as f1, open(sample_path, "rb") as f2:
            print("Submitting Job 1...")
            res1 = await client.post("/api/v1/jobs/upload", files={"file": ("sample1.mp4", f1, "video/mp4")})
            
            print("Submitting Job 2...")
            res2 = await client.post("/api/v1/jobs/upload", files={"file": ("sample2.mp4", f2, "video/mp4")})
            
        if res1.status_code != 200 or res2.status_code != 200:
            print(f"Upload failed: {res1.status_code}, {res2.status_code}")
            return
            
        job1_id = res1.json()["job_id"]
        job2_id = res2.json()["job_id"]
        
        print(f"Job 1 ID: {job1_id}")
        print(f"Job 2 ID: {job2_id}")
        
        # Monitor both concurrently
        await asyncio.gather(
            poll_job(client, job1_id, "Job 1"),
            poll_job(client, job2_id, "Job 2")
        )

if __name__ == "__main__":
    os.environ["SECRET_KEY"] = "test-secret-key"
    asyncio.run(run_concurrent_jobs())
