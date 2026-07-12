import os
import shutil
from fastapi import UploadFile, BackgroundTasks
from core.job_manager import JobManager, JobStatus, Job
from config.settings import Settings
from core.exceptions import UnsupportedFormatError
from core.logging import logger
from tracker.detector import YoloDetector
from services.video_service import process_video_file
from typing import Optional

from core.execution.base import ExecutionBackend

def _process_video_wrapper(input_path: str, output_path: str, job_id: str, yolo_model_path: str):
    """Picklable wrapper for running video processing in a separate process."""
    from core.job_manager import JobManager
    from tracker.detector import plugin_manager
    from config.settings import get_cached_settings
    
    settings = get_cached_settings()
    job_manager = JobManager()
    
    # We load the generic YOLO model or use the plugin
    # Here we assume the default model is loaded
    from core.dependencies import get_model_manager
    model_manager = get_model_manager()
    detector = model_manager.get_yolo_model(yolo_model_path)
    
    from services.video_service import process_video_file
    return process_video_file(
        input_path=input_path,
        output_path=output_path,
        detector=detector,
        settings=settings,
        job_id=job_id,
        job_manager=job_manager
    )

class JobService:
    def __init__(self, job_manager: JobManager, settings: Settings, detector: YoloDetector, execution_backend: ExecutionBackend):
        self.job_manager = job_manager
        self.settings = settings
        self.detector = detector
        self.execution_backend = execution_backend

    async def upload_video(
        self, 
        file: UploadFile, 
        user_id: str, 
        background_tasks: BackgroundTasks, 
        project_id: Optional[str] = None
    ) -> Job:
        logger.info(f"Received request to create job for file: {file.filename}")
        
        if not file.filename.lower().endswith((".mp4", ".avi", ".mov")):
            raise UnsupportedFormatError(f"File {file.filename} is not a supported video format.")
            
        os.makedirs(self.settings.temp_dir, exist_ok=True)
        os.makedirs(self.settings.output_dir, exist_ok=True)
        
        job = await self.job_manager.create_job(filename=file.filename, user_id=user_id, project_id=project_id)
        await self.job_manager.update_job(job.id, status=JobStatus.INITIALIZING, stage="Saving file")
        
        input_filename = f"{job.id}_{file.filename}"
        output_filename = f"tracked_{job.id}_{file.filename}"
        
        job_output_dir = os.path.join(self.settings.output_dir, str(job.id))
        os.makedirs(job_output_dir, exist_ok=True)
        
        input_path = os.path.join(self.settings.temp_dir, input_filename)
        output_path = os.path.join(job_output_dir, output_filename)
        
        # Save the uploaded file to disk
        with open(input_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        logger.info(f"File saved to temp path: {input_path}")
            
        # Kick off processing using the dedicated execution backend
        self.execution_backend.submit_job(
            _process_video_wrapper,
            input_path=input_path,
            output_path=output_path,
            job_id=job.id,
            yolo_model_path=self.settings.yolo_model_path
        )
        
        return job

    async def delete_job(self, job_id: str) -> bool:
        job = await self.job_manager.get_job(job_id)
        if not job:
            return False
            
        # Attempt to clean up files
        if job.output_path and os.path.exists(job.output_path):
            try:
                os.remove(job.output_path)
            except Exception as e:
                logger.warning(f"Failed to delete output file {job.output_path}: {e}")
                
        return await self.job_manager.delete_job(job_id)
