from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)

def test_process_video():
    # Use our existing sample video
    with open("data/sample_videos/sample.mp4", "rb") as f:
        response = client.post("/process-video", files={"file": ("sample.mp4", f, "video/mp4")})
        
    assert response.status_code == 200
    assert "X-Analytics-Summary" in response.headers
    
    print("API test passed successfully!")
    print(f"Headers: {response.headers['X-Analytics-Summary']}")

if __name__ == "__main__":
    test_process_video()
