from enum import Enum
from pydantic import BaseModel, Field
from typing import Dict, Optional, Any
from datetime import datetime
import uuid
import json

from db.database import SessionLocal
from db.models import Job as JobDB
from core.events import event_bus, EventType
from core.logging import logger
from sqlalchemy.future import select

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
    Job management system synchronized with PostgreSQL via SQLAlchemy Async.
    """
    def __init__(self):
        self._jobs: Dict[str, Job] = {}
        
    async def initialize(self):
        await self._sync_active_jobs_from_db()
        
    async def _sync_active_jobs_from_db(self):
        async with SessionLocal() as db:
            try:
                result = await db.execute(
                    select(JobDB).filter(JobDB.status.in_([JobStatus.QUEUED.value, JobStatus.INITIALIZING.value, JobStatus.PROCESSING.value]))
                )
                active_jobs = result.scalars().all()
                if active_jobs:
                    logger.warning(f"Aborting {len(active_jobs)} active jobs due to server restart.")
                    for db_job in active_jobs:
                        db_job.status = JobStatus.FAILED.value
                        db_job.error = "Job aborted due to server restart."
                    await db.commit()
            except Exception as e:
                await db.rollback()
                logger.error(f"Error syncing active jobs: {e}")

    async def create_job(self, filename: str, user_id: str = None, project_id: str = None) -> Job:
        job = Job(filename=filename, user_id=user_id, project_id=project_id)
        self._jobs[job.id] = job
        
        async with SessionLocal() as db:
            try:
                db_job = JobDB(
                    id=job.id,
                    filename=job.filename,
                    status=job.status.value,
                    user_id=job.user_id,
                    project_id=job.project_id
                )
                db.add(db_job)
                await db.commit()
            except Exception as e:
                await db.rollback()
                logger.error(f"Failed to create job in DB: {e}")
            
        event_bus.publish(EventType.JOB_CREATED, {"job_id": job.id, "filename": job.filename})
        return job

    async def get_job(self, job_id: str) -> Optional[Job]:
        if job_id in self._jobs:
            return self._jobs[job_id]
            
        async with SessionLocal() as db:
            result = await db.execute(select(JobDB).filter(JobDB.id == job_id))
            db_job = result.scalar_one_or_none()
            if db_job:
                analytics = None
                if db_job.analytics:
                    analytics = json.loads(db_job.analytics)
                
                job = Job(
                    id=db_job.id,
                    filename=db_job.filename,
                    status=JobStatus(db_job.status),
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
                self._jobs[job.id] = job
                return job
        return None

    async def update_job(
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
        job = await self.get_job(job_id)
        if not job:
            return None
            
        old_status = job.status
        if status is not None:
            job.status = status
            if status in [JobStatus.COMPLETED, JobStatus.FAILED]:
                job.completion_time = datetime.utcnow()
                job.duration = (job.completion_time - job.start_time).total_seconds()
                if status == JobStatus.COMPLETED:
                    job.progress = 100.0
                    event_bus.publish(EventType.JOB_COMPLETED, {"job_id": job.id, "duration": job.duration})
                else:
                    event_bus.publish(EventType.JOB_FAILED, {"job_id": job.id, "error": error})
            elif status == JobStatus.PROCESSING and old_status != JobStatus.PROCESSING:
                event_bus.publish(EventType.JOB_STARTED, {"job_id": job.id})
                    
        if progress is not None: job.progress = progress
        if stage is not None: job.stage = stage
        if error is not None: job.error = error
        if output_path is not None: job.output_path = output_path
        if analytics is not None: job.analytics = analytics
        if average_fps is not None: job.average_fps = average_fps
        if processing_throughput is not None: job.processing_throughput = processing_throughput
            
        if (status is not None and status != old_status) or job.status in [JobStatus.COMPLETED, JobStatus.FAILED] or analytics is not None:
            async with SessionLocal() as db:
                try:
                    result = await db.execute(select(JobDB).filter(JobDB.id == job_id))
                    db_job = result.scalar_one_or_none()
                    if db_job:
                        db_job.status = job.status.value
                        db_job.progress = job.progress
                        db_job.stage = job.stage
                        if error is not None: db_job.error = job.error
                        if output_path is not None: db_job.output_path = job.output_path
                        if average_fps is not None: db_job.average_fps = job.average_fps
                        if processing_throughput is not None: db_job.processing_throughput = job.processing_throughput
                        if analytics is not None: db_job.analytics = json.dumps(job.analytics)
                        if job.completion_time:
                            db_job.completion_time = job.completion_time
                            db_job.duration = job.duration
                        
                        await db.commit()
                except Exception as e:
                    await db.rollback()
                    logger.error(f"Failed to update job {job_id} in DB: {e}")
                    
        event_bus.publish(EventType.JOB_UPDATED, {"job_id": job_id, "status": job.status.value, "progress": job.progress})
        
        if job.status in [JobStatus.COMPLETED, JobStatus.FAILED]:
            if job_id in self._jobs:
                del self._jobs[job_id]
                
        return job

    def get_all_jobs(self) -> Dict[str, Job]:
        return self._jobs.copy()

    async def delete_job(self, job_id: str) -> bool:
        if job_id in self._jobs:
            del self._jobs[job_id]
            
        async with SessionLocal() as db:
            try:
                result = await db.execute(select(JobDB).filter(JobDB.id == job_id))
                db_job = result.scalar_one_or_none()
                if db_job:
                    await db.delete(db_job)
                    await db.commit()
                    return True
            except Exception as e:
                await db.rollback()
                logger.error(f"Failed to delete job {job_id} from DB: {e}")
        return False
