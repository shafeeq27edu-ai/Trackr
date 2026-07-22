import threading
from typing import Any, Callable, Dict

from core.execution.base import ExecutionBackend
from core.logging import logger


class LocalExecutionBackend(ExecutionBackend):
    """
    Local execution backend that runs tasks in a background thread or registers
    them via FastAPI's BackgroundTasks.
    Useful for local development and testing without Celery/Redis.
    """

    def __init__(self):
        self._statuses: Dict[str, str] = {}

    def submit_job(self, task: Callable, *args, **kwargs) -> str:
        job_id = kwargs.get("job_id") or "local-job"
        logger.info(f"Submitting job locally for task: {task.__name__} (job_id: {job_id})")
        self._statuses[job_id] = "PROCESSING"

        background_tasks = kwargs.pop("background_tasks", None)
        if background_tasks is not None:
            background_tasks.add_task(task, *args, **kwargs)
            self._statuses[job_id] = "SUCCESS"
        else:

            def run_thread():
                try:
                    task(*args, **kwargs)
                    self._statuses[job_id] = "SUCCESS"
                except Exception as e:
                    logger.error(
                        f"Local task execution failed for job {job_id}: {e}", exc_info=True
                    )
                    self._statuses[job_id] = "FAILURE"

            thread = threading.Thread(target=run_thread, daemon=True)
            thread.start()

        return job_id

    def get_job_status(self, job_id: str) -> Dict[str, Any]:
        status = self._statuses.get(job_id, "PENDING")
        return {"status": status}
