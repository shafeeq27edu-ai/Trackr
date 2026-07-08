from enum import Enum
from pydantic import BaseModel, Field
from typing import Dict, Optional, Any
from datetime import datetime
import uuid

class JobStatus(str, Enum):
    QUEUED = "QUEUED"
    INITIALIZING = "INITIALIZING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class Job(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    filename: str
    status: JobStatus = JobStatus.QUEUED
    progress: float = 0.0
    stage: str = "Job created"
    start_time: datetime = Field(default_factory=datetime.utcnow)
    completion_time: Optional[datetime] = None
    duration: Optional[float] = None
    error: Optional[str] = None
    output_path: Optional[str] = None
    analytics: Optional[Dict[str, Any]] = None

class JobManager:
    """
    In-memory job management system.
    Designed to be easily replaceable with Redis/Celery in the future.
    """
    def __init__(self):
        self._jobs: Dict[str, Job] = {}

    def create_job(self, filename: str) -> Job:
        job = Job(filename=filename)
        self._jobs[job.id] = job
        return job

    def get_job(self, job_id: str) -> Optional[Job]:
        return self._jobs.get(job_id)

    def update_job(
        self, 
        job_id: str, 
        status: Optional[JobStatus] = None, 
        progress: Optional[float] = None, 
        stage: Optional[str] = None,
        error: Optional[str] = None,
        output_path: Optional[str] = None,
        analytics: Optional[Dict[str, int]] = None
    ) -> Optional[Job]:
        job = self._jobs.get(job_id)
        if not job:
            return None
            
        if status is not None:
            job.status = status
            if status in [JobStatus.COMPLETED, JobStatus.FAILED]:
                job.completion_time = datetime.utcnow()
                job.duration = (job.completion_time - job.start_time).total_seconds()
                if status == JobStatus.COMPLETED:
                    job.progress = 100.0
                    
        if progress is not None:
            job.progress = progress
        if stage is not None:
            job.stage = stage
        if error is not None:
            job.error = error
        if output_path is not None:
            job.output_path = output_path
        if analytics is not None:
            job.analytics = analytics
            
        return job

    def delete_job(self, job_id: str) -> bool:
        if job_id in self._jobs:
            del self._jobs[job_id]
            return True
        return False

    def list_jobs(self) -> Dict[str, Job]:
        return self._jobs
