import os
from celery import Celery
import asyncio
from core.job_manager import JobManager, JobStatus
from core.logging import logger

redis_url = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")

celery_app = Celery("trackr_worker", broker=redis_url, backend=redis_url)


@celery_app.task(bind=True)
def process_video_task(self, job_id: str, input_path: str, output_path: str, yolo_model_path: str):
    logger.info(f"Starting background job {job_id} for file {input_path}")

    from services.job_service import _process_video_wrapper

    try:
        # Actually run the video pipeline
        _process_video_wrapper(
            input_path=input_path,
            output_path=output_path,
            job_id=job_id,
            yolo_model_path=yolo_model_path,
        )
        logger.info(f"Completed background job {job_id}")
        return {"status": "SUCCESS", "job_id": job_id}
    except Exception as e:
        logger.error(f"Task failed for job {job_id}: {str(e)}", exc_info=True)
        # JobStatus is already updated by _process_video_wrapper or video_service
        return {"status": "FAILED", "job_id": job_id, "error": str(e)}
