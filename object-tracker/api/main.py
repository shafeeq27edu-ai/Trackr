import os
import shutil
import uuid
import json
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Dict
from services.video_service import process_video_file

app = FastAPI(title="Trackr API", description="Computer Vision Object Tracking Backend")

class ProcessResult(BaseModel):
    message: str
    unique_counts: Dict[str, int]

@app.post("/process-video")
def process_video(file: UploadFile = File(...)):
    """
    Accepts a video upload, runs the object tracking pipeline, and returns the annotated video.
    Note: Standard `def` endpoints run in a threadpool, preventing this CPU-bound task from blocking the event loop.
    """
    # Create temporary directories if they don't exist
    temp_dir = "data/temp"
    output_dir = "outputs/api"
    os.makedirs(temp_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate unique filenames
    file_id = str(uuid.uuid4())
    input_filename = f"{file_id}_{file.filename}"
    output_filename = f"tracked_{file_id}_{file.filename}"
    
    input_path = os.path.join(temp_dir, input_filename)
    output_path = os.path.join(output_dir, output_filename)
    
    # Save the uploaded file to disk
    with open(input_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    # Process the video via our service layer (business logic)
    counts = process_video_file(input_path, output_path)
    
    # Return the processed video along with custom headers containing analytics
    headers = {
        "X-Analytics-Summary": json.dumps(counts)
    }
    
    return FileResponse(
        path=output_path,
        media_type="video/mp4",
        filename=output_filename,
        headers=headers
    )
