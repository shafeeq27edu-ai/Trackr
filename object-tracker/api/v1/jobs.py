import os
import shutil
import uuid
import json
from fastapi import APIRouter, UploadFile, File, Depends, BackgroundTasks, HTTPException, Form
from fastapi.responses import FileResponse, JSONResponse
from typing import Dict, List, Optional
from services.video_service import process_video_file
from core.dependencies import get_detector, get_settings, get_job_manager
from tracker.detector import YoloDetector
from config.settings import Settings
from core.exceptions import UnsupportedFormatError
from core.job_manager import JobManager, JobStatus, Job
from core.logging import logger
from api.deps import get_current_user
from db.models import User

router = APIRouter()

@router.post("/jobs/upload")
def create_job(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    project_id: Optional[str] = Form(None),
    detector: YoloDetector = Depends(get_detector),
    settings: Settings = Depends(get_settings),
    job_manager: JobManager = Depends(get_job_manager),
    current_user: User = Depends(get_current_user)
):
    """
    Accepts a video upload, creates a new job, kicks off processing in the background, 
    and returns the job ID immediately.
    """
    logger.info(f"Received request to create job for file: {file.filename}")
    
    if not file.filename.lower().endswith((".mp4", ".avi", ".mov")):
        raise UnsupportedFormatError(f"File {file.filename} is not a supported video format.")
        
    os.makedirs(settings.temp_dir, exist_ok=True)
    os.makedirs(settings.output_dir, exist_ok=True)
    
    job = job_manager.create_job(filename=file.filename, user_id=current_user.id, project_id=project_id)
    job_manager.update_job(job.id, status=JobStatus.INITIALIZING, stage="Saving file")
    
    input_filename = f"{job.id}_{file.filename}"
    output_filename = f"tracked_{job.id}_{file.filename}"
    
    input_path = os.path.join(settings.temp_dir, input_filename)
    output_path = os.path.join(settings.output_dir, output_filename)
    
    # Save the uploaded file to disk
    with open(input_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    logger.info(f"File saved to temp path: {input_path}")
        
    # Kick off background task
    background_tasks.add_task(
        process_video_file,
        input_path=input_path,
        output_path=output_path,
        detector=detector,
        settings=settings,
        job_id=job.id,
        job_manager=job_manager
    )
    
    return {"job_id": job.id, "status": job.status, "message": "Job successfully queued for processing."}

@router.get("/jobs/{job_id}", response_model=Job)
def get_job_status(job_id: str, job_manager: JobManager = Depends(get_job_manager), current_user: User = Depends(get_current_user)):
    job = job_manager.get_job(job_id)
    if not job or (job.user_id and job.user_id != current_user.id):
        raise HTTPException(status_code=404, detail="Job not found")
    return job

@router.get("/jobs/{job_id}/result")
def get_job_result(job_id: str, job_manager: JobManager = Depends(get_job_manager), current_user: User = Depends(get_current_user)):
    job = job_manager.get_job(job_id)
    if not job or (job.user_id and job.user_id != current_user.id):
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.status != JobStatus.COMPLETED or not job.output_path:
        raise HTTPException(status_code=400, detail="Job is not completed yet.")
        
    if not os.path.exists(job.output_path):
        raise HTTPException(status_code=404, detail="Processed video file not found.")
        
    return FileResponse(
        path=job.output_path,
        media_type="video/mp4",
        filename=os.path.basename(job.output_path)
    )

@router.get("/jobs/{job_id}/analytics")
def get_job_analytics(job_id: str, job_manager: JobManager = Depends(get_job_manager), current_user: User = Depends(get_current_user)):
    job = job_manager.get_job(job_id)
    if not job or (job.user_id and job.user_id != current_user.id):
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status != JobStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Job is not completed yet.")
        
    return JSONResponse(content={"analytics": job.analytics})

@router.get("/jobs/{job_id}/heatmap")
def get_job_heatmap(job_id: str, job_manager: JobManager = Depends(get_job_manager), current_user: User = Depends(get_current_user)):
    job = job_manager.get_job(job_id)
    if not job or (job.user_id and job.user_id != current_user.id) or job.status != JobStatus.COMPLETED or not job.output_path:
        raise HTTPException(status_code=404, detail="Heatmap not available yet.")
        
    job_dir = os.path.dirname(job.output_path)
    heatmap_path = os.path.join(job_dir, f"heatmap_{job_id}.png")
    
    if not os.path.exists(heatmap_path):
        raise HTTPException(status_code=404, detail="Heatmap file not found.")
        
    return FileResponse(
        path=heatmap_path,
        media_type="image/png",
        filename=f"heatmap_{job_id}.png"
    )

@router.get("/jobs/{job_id}/report")
def get_job_report(job_id: str, job_manager: JobManager = Depends(get_job_manager), current_user: User = Depends(get_current_user)):
    job = job_manager.get_job(job_id)
    if not job or (job.user_id and job.user_id != current_user.id) or job.status != JobStatus.COMPLETED or not job.output_path:
        raise HTTPException(status_code=404, detail="Report not available yet.")
        
    job_dir = os.path.dirname(job.output_path)
    csv_path = os.path.join(job_dir, "logs.csv")
    
    if not os.path.exists(csv_path):
        raise HTTPException(status_code=404, detail="CSV report not found.")
        
    return FileResponse(
        path=csv_path,
        media_type="text/csv",
        filename=f"report_{job_id}.csv"
    )

@router.get("/jobs")
def list_jobs(job_manager: JobManager = Depends(get_job_manager), current_user: User = Depends(get_current_user)):
    jobs = job_manager.list_jobs()
    # Filter by user
    user_jobs = [job.model_dump() for job in jobs.values() if job.user_id == current_user.id]
    return {"jobs": user_jobs}

@router.delete("/jobs/{job_id}")
def delete_job(job_id: str, job_manager: JobManager = Depends(get_job_manager), current_user: User = Depends(get_current_user)):
    job = job_manager.get_job(job_id)
    if not job or (job.user_id and job.user_id != current_user.id):
        raise HTTPException(status_code=404, detail="Job not found")
        
    # Attempt to clean up files
    if job.output_path and os.path.exists(job.output_path):
        try:
            os.remove(job.output_path)
        except Exception as e:
            logger.warning(f"Failed to delete output file {job.output_path}: {e}")
            
    success = job_manager.delete_job(job_id)
    return {"success": success, "message": "Job deleted successfully"}
