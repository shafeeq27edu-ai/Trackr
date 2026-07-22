import os
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse

from api.deps import get_current_user
from core.dependencies import get_job_manager, get_job_service
from core.job_manager import Job, JobManager, JobStatus
from db.models import User
from services.job_service import JobService

router = APIRouter()


@router.post("/jobs/upload")
async def create_job(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    project_id: Optional[str] = Form(None),
    job_service: JobService = Depends(get_job_service),
    current_user: User = Depends(get_current_user),
):
    """
    Accepts a video upload, creates a new job, kicks off processing in the background,
    and returns the job ID immediately.
    """
    job = await job_service.upload_video(file, current_user.id, background_tasks, project_id)
    return {
        "job_id": job.id,
        "status": job.status,
        "message": "Job successfully queued for processing.",
    }


@router.get("/jobs/{job_id}", response_model=Job)
async def get_job_status(
    job_id: str,
    job_manager: JobManager = Depends(get_job_manager),
    current_user: User = Depends(get_current_user),
):
    job = await job_manager.get_job(job_id)
    if not job or (job.user_id and job.user_id != current_user.id):
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("/jobs/{job_id}/result")
# SECURITY WARNING: This endpoint allows authentication via `?token=` query parameter.
# This exposes the JWT in browser history, server logs, and Referer headers.
# Future improvement: Use short-lived signed URLs for media downloads instead of the main JWT.
async def get_job_result(
    job_id: str,
    job_manager: JobManager = Depends(get_job_manager),
    current_user: User = Depends(get_current_user),
):
    job = await job_manager.get_job(job_id)
    if not job or (job.user_id and job.user_id != current_user.id):
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status != JobStatus.COMPLETED or not job.output_path:
        raise HTTPException(status_code=400, detail="Job is not completed yet.")

    if not os.path.exists(job.output_path):
        raise HTTPException(status_code=404, detail="Processed video file not found.")

    return FileResponse(
        path=job.output_path, media_type="video/mp4", filename=os.path.basename(job.output_path)
    )


@router.get("/jobs/{job_id}/analytics")
async def get_job_analytics(
    job_id: str,
    job_manager: JobManager = Depends(get_job_manager),
    current_user: User = Depends(get_current_user),
):
    job = await job_manager.get_job(job_id)
    if not job or (job.user_id and job.user_id != current_user.id):
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status != JobStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Job is not completed yet.")

    return JSONResponse(content={"analytics": job.analytics})


@router.get("/jobs/{job_id}/heatmap")
async def get_job_heatmap(
    job_id: str,
    job_manager: JobManager = Depends(get_job_manager),
    current_user: User = Depends(get_current_user),
):
    job = await job_manager.get_job(job_id)
    if (
        not job
        or (job.user_id and job.user_id != current_user.id)
        or job.status != JobStatus.COMPLETED
        or not job.output_path
    ):
        raise HTTPException(status_code=404, detail="Heatmap not available yet.")

    job_dir = os.path.dirname(job.output_path)
    heatmap_path = os.path.join(job_dir, f"heatmap_{job_id}.png")

    if not os.path.exists(heatmap_path):
        raise HTTPException(status_code=404, detail="Heatmap file not found.")

    return FileResponse(path=heatmap_path, media_type="image/png", filename=f"heatmap_{job_id}.png")


@router.get("/jobs/{job_id}/report")
async def get_job_report(
    job_id: str,
    job_manager: JobManager = Depends(get_job_manager),
    current_user: User = Depends(get_current_user),
):
    job = await job_manager.get_job(job_id)
    if (
        not job
        or (job.user_id and job.user_id != current_user.id)
        or job.status != JobStatus.COMPLETED
        or not job.output_path
    ):
        raise HTTPException(status_code=404, detail="Report not available yet.")

    job_dir = os.path.dirname(job.output_path)
    csv_path = os.path.join(job_dir, "logs.csv")

    if not os.path.exists(csv_path):
        raise HTTPException(status_code=404, detail="CSV report not found.")

    return FileResponse(path=csv_path, media_type="text/csv", filename=f"report_{job_id}.csv")


@router.get("/jobs")
async def list_jobs(
    job_manager: JobManager = Depends(get_job_manager),
    current_user: User = Depends(get_current_user),
):
    jobs = await job_manager.get_all_jobs()
    # Filter by user
    user_jobs = [job.model_dump() for job in jobs.values() if job.user_id == current_user.id]
    return {"jobs": user_jobs}


@router.delete("/jobs/{job_id}")
async def delete_job(
    job_id: str,
    job_service: JobService = Depends(get_job_service),
    current_user: User = Depends(get_current_user),
    job_manager: JobManager = Depends(get_job_manager),
):
    job = await job_manager.get_job(job_id)
    if not job or (job.user_id and job.user_id != current_user.id):
        raise HTTPException(status_code=404, detail="Job not found")

    success = await job_service.delete_job(job_id)
    return {"success": success, "message": "Job deleted successfully"}
