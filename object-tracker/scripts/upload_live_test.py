import uuid
import requests
import time
import cv2
import numpy as np
import os

API_URL = "http://localhost:8000/api/v1"

def create_dummy_video(filename="test_video.mp4"):
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(filename, fourcc, 20.0, (640, 480))
    for i in range(60): # 3 seconds
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        cv2.putText(frame, f"Frame {i}", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        out.write(frame)
    out.release()
    return filename

def run_e2e_test():
    # 1. Register/Login
    email = f"e2e_{uuid.uuid4().hex[:6]}@example.com"
    pwd = "password123"
    print(f"Registering user {email}...")
    requests.post(f"{API_URL}/auth/register", json={"email": email, "password": pwd, "name": "E2E User"})
    
    res = requests.post(f"{API_URL}/auth/login", data={"username": email, "password": pwd})
    token = res.json().get("access_token")
    headers = {"Authorization": f"Bearer {token}"}
    
    # 2. Create and Upload Video
    video_path = create_dummy_video()
    print(f"Uploading {video_path}...")
    with open(video_path, 'rb') as f:
        res = requests.post(f"{API_URL}/jobs/upload", files={"file": (video_path, f, "video/mp4")}, headers=headers)
    
    if res.status_code != 200:
        print("Upload failed:", res.text)
        return
        
    job_id = res.json()["job_id"]
    print(f"Upload successful. Job ID: {job_id}")
    
    # 3. Poll for completion
    while True:
        res = requests.get(f"{API_URL}/jobs/{job_id}", headers=headers)
        status = res.json()["status"]
        print(f"Job Status: {status}")
        if status in ["COMPLETED", "FAILED"]:
            break
        time.sleep(2)
        
    if status == "COMPLETED":
        # 4. Verify endpoints
        res_vid = requests.get(f"{API_URL}/jobs/{job_id}/result", headers=headers)
        res_hm = requests.get(f"{API_URL}/jobs/{job_id}/heatmap", headers=headers)
        res_rep = requests.get(f"{API_URL}/jobs/{job_id}/report", headers=headers)
        
        print(f"Result Video Download: HTTP {res_vid.status_code} ({len(res_vid.content)} bytes)")
        print(f"Heatmap Download: HTTP {res_hm.status_code} ({len(res_hm.content)} bytes)")
        print(f"CSV Report Download: HTTP {res_rep.status_code} ({len(res_rep.content)} bytes)")
        print("End-to-end video processing verified successfully!")
    else:
        print("Job failed.")
        
if __name__ == "__main__":
    run_e2e_test()
