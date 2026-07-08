import os
import shutil
import uuid
import json
from fastapi import APIRouter, UploadFile, File, Depends
from fastapi.responses import FileResponse
from typing import Dict
from services.video_service import process_video_file
from core.dependencies import get_detector, get_settings
from tracker.detector import YoloDetector
from config.settings import Settings
from core.exceptions import UnsupportedFormatError
from core.logging import logger

router = APIRouter()

@router.post("/process/video")
def process_video(
    file: UploadFile = File(...),
    detector: YoloDetector = Depends(get_detector),
    settings: Settings = Depends(get_settings)
):
    """
    Accepts a video upload, runs the object tracking pipeline using the globally injected model,
    and returns the annotated video with tracking metrics in headers.
    """
    logger.info(f"Received request to process video upload: {file.filename}")
    
    if not file.filename.lower().endswith((".mp4", ".avi", ".mov")):
        raise UnsupportedFormatError(f"File {file.filename} is not a supported video format.")
        
    os.makedirs(settings.temp_dir, exist_ok=True)
    os.makedirs(settings.output_dir, exist_ok=True)
    
    # Generate unique filenames
    file_id = str(uuid.uuid4())
    input_filename = f"{file_id}_{file.filename}"
    output_filename = f"tracked_{file_id}_{file.filename}"
    
    input_path = os.path.join(settings.temp_dir, input_filename)
    output_path = os.path.join(settings.output_dir, output_filename)
    
    # Save the uploaded file to disk
    with open(input_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    logger.info(f"File saved to temp path: {input_path}")
        
    # Process the video via our service layer using injected dependencies
    counts = process_video_file(input_path, output_path, detector, settings)
    
    # Return the processed video along with custom headers containing analytics
    headers = {
        "X-Analytics-Summary": json.dumps(counts)
    }
    
    logger.info(f"Returning processed video: {output_path}")
    
    return FileResponse(
        path=output_path,
        media_type="video/mp4",
        filename=output_filename,
        headers=headers
    )
