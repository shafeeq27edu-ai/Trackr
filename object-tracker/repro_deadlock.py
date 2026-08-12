import asyncio
import threading
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.main import app
from core.models.registry import model_registry
import numpy as np

def run_test():
    # First TestClient cycle (like test_jobs.py)
    with TestClient(app) as client:
        pass
    
    print("First client closed. YOLO should be in memory.")
    
    # Second TestClient cycle (like test_pipeline.py)
    with TestClient(app) as client:
        print("Second client opened. Spawning thread...")
        
        def bg_thread():
            print("Background thread started. Running inference...")
            async def run_async():
                detector = model_registry.get_model("yolov8n.pt")
                
                # Create a dummy frame
                frame = np.zeros((640, 640, 3), dtype=np.uint8)
                frames = [frame]
                
                print("Calling detect_batch...")
                res = detector.detect_batch(frames)
                print("Inference completed!", len(res))
            
            import asyncio
            asyncio.run(run_async())
            
        t = threading.Thread(target=bg_thread)
        t.start()
        t.join(timeout=10)
        
        if t.is_alive():
            print("ERROR: Thread HUNG!")
        else:
            print("SUCCESS: Thread finished.")

if __name__ == "__main__":
    run_test()
