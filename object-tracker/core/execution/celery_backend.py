from typing import Any, Callable, Dict

from core.execution.base import ExecutionBackend
from core.logging import logger


class CeleryExecutionBackend(ExecutionBackend):
    """
    Distributed execution backend using Celery & Redis.
    """

    def __init__(self, app):
        self.app = app

    def submit_job(self, task: Callable, *args, **kwargs) -> str:
        logger.info(f"Submitting job via Celery for task: {task.__name__}")

        # If the task is _process_video_wrapper, we dispatch to our Celery task.
        if task.__name__ == "_process_video_wrapper":
            from core.execution.worker import process_video_task

            logger.info(
                f"DISPATCHING TASK TO CELERY: job_id={kwargs.get('job_id')} "
                f"input={kwargs.get('input_path')}"
            )
            result = process_video_task.delay(**kwargs)
            return result.id
        else:
            logger.error("Unknown task submitted to Celery Backend")
            return "unknown-task"

    def get_job_status(self, job_id: str) -> Dict[str, Any]:
        result = self.app.AsyncResult(job_id)
        return {"status": result.state}
