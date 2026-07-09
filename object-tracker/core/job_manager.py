from enum import Enum
from pydantic import BaseModel, Field
from typing import Dict, Optional, Any
from datetime import datetime
import uuid
import json

from db.database import SessionLocal
from db.models import Job as JobDB

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
    average_fps: Optional[float] = None
    processing_throughput: Optional[float] = None
    user_id: Optional[str] = None
    project_id: Optional[str] = None

class JobManager:
    """
    Job management system synchronized with SQLite via SQLAlchemy.
    Maintains an in-memory dictionary for fast reads (like active progress) 
    but persists to the database.
    """
    def __init__(self):
        self._jobs: Dict[str, Job] = {}
        self._sync_active_jobs_from_db()
        
    def _sync_active_jobs_from_db(self):
        db = SessionLocal()
        try:
            # We could load active jobs here if needed, but for now we trust new requests.
            pass
        finally:
            db.close()

    def create_job(self, filename: str, user_id: str = None, project_id: str = None) -> Job:
        job = Job(filename=filename, user_id=user_id, project_id=project_id)
        self._jobs[job.id] = job
        
        # Persist to DB
        db = SessionLocal()
        try:
            db_job = JobDB(
                id=job.id,
                filename=job.filename,
                status=job.status,
                user_id=job.user_id,
                project_id=job.project_id
            )
            db.add(db_job)
            db.commit()
        except Exception as e:
            # log exception
            pass
        finally:
            db.close()
            
        return job

    def get_job(self, job_id: str) -> Optional[Job]:
        # Try memory first (for active processing jobs)
        if job_id in self._jobs:
            return self._jobs[job_id]
            
        # Fallback to DB
        db = SessionLocal()
        try:
            db_job = db.query(JobDB).filter(JobDB.id == job_id).first()
            if db_job:
                analytics = None
                if db_job.analytics:
                    analytics = json.loads(db_job.analytics)
                    
                job = Job(
                    id=db_job.id,
                    filename=db_job.filename,
                    status=db_job.status,
                    progress=db_job.progress,
                    stage=db_job.stage,
                    start_time=db_job.start_time,
                    completion_time=db_job.completion_time,
                    duration=db_job.duration,
                    error=db_job.error,
                    output_path=db_job.output_path,
                    analytics=analytics,
                    average_fps=db_job.average_fps,
                    processing_throughput=db_job.processing_throughput,
                    user_id=db_job.user_id,
                    project_id=db_job.project_id
                )
                return job
            return None
        finally:
            db.close()

    def update_job(
        self, 
        job_id: str, 
        status: Optional[JobStatus] = None, 
        progress: Optional[float] = None, 
        stage: Optional[str] = None,
        error: Optional[str] = None,
        output_path: Optional[str] = None,
        analytics: Optional[Dict[str, Any]] = None,
        average_fps: Optional[float] = None,
        processing_throughput: Optional[float] = None
    ) -> Optional[Job]:
        job = self.get_job(job_id)
        if not job:
            return None
            
        # Update memory model
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
        if average_fps is not None:
            job.average_fps = average_fps
        if processing_throughput is not None:
            job.processing_throughput = processing_throughput
            
        # Update DB
        db = SessionLocal()
        try:
            db_job = db.query(JobDB).filter(JobDB.id == job_id).first()
            if db_job:
                db_job.status = job.status
                db_job.progress = job.progress
                db_job.stage = job.stage
                db_job.completion_time = job.completion_time
                db_job.duration = job.duration
                db_job.error = job.error
                db_job.output_path = job.output_path
                if job.analytics:
                    db_job.analytics = json.dumps(job.analytics)
                db_job.average_fps = job.average_fps
                db_job.processing_throughput = job.processing_throughput
                db.commit()
        finally:
            db.close()
            
        # Cleanup from memory if finished to save RAM, rely on DB for future queries
        if job.status in [JobStatus.COMPLETED, JobStatus.FAILED] and job_id in self._jobs:
            # We'll leave it in memory for a short while, or just keep it since dict is small.
            # Real-world we might evict it.
            pass
            
        return job

    def delete_job(self, job_id: str) -> bool:
        if job_id in self._jobs:
            del self._jobs[job_id]
            
        db = SessionLocal()
        try:
            db_job = db.query(JobDB).filter(JobDB.id == job_id).first()
            if db_job:
                db.delete(db_job)
                db.commit()
                return True
        finally:
            db.close()
        return False

    def list_jobs(self) -> Dict[str, Job]:
        return self._jobs
