from typing import Callable, Any, Dict
from core.execution.base import ExecutionBackend
from core.logging import logger

class CeleryExecutionBackend(ExecutionBackend):
    """
    Distributed execution backend using Celery & Redis.
    """
    
    def __init__(self, app):
        self.app = app

    def submit_job(self, task: Callable, *args, **kwargs) -> str:
        logger.info(f"Submitting job via Celery: {task.__name__}")
        
        result = task.delay(*args, **kwargs)
        return result.id

    def get_job_status(self, job_id: str) -> Dict[str, Any]:
        result = self.app.AsyncResult(job_id)
        return {"status": result.state}
