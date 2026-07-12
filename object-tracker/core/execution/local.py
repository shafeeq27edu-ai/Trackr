from concurrent.futures import ProcessPoolExecutor
import uuid
from typing import Callable, Any, Dict
from core.execution.base import ExecutionBackend
from core.logging import logger

class LocalExecutionBackend(ExecutionBackend):
    """Local execution backend using a process pool to bypass the GIL."""
    
    def __init__(self, max_workers: int = 4):
        self.executor = ProcessPoolExecutor(max_workers=max_workers)
        self.futures = {}

    def submit_job(self, task: Callable, *args, **kwargs) -> str:
        # In a real system, the task might already have a job_id. 
        # For our wrapper, we generate an internal execution id if needed,
        # but usually the job_manager tracks the job_id. We'll just return a UUID.
        execution_id = str(uuid.uuid4())
        logger.info(f"Submitting job to LocalExecutionBackend (exec_id: {execution_id})")
        
        future = self.executor.submit(task, *args, **kwargs)
        self.futures[execution_id] = future
        
        # Add a callback to log exceptions
        def done_callback(fut):
            try:
                fut.result()
            except Exception as e:
                logger.error(f"Task {execution_id} failed with exception: {e}")
                
        future.add_done_callback(done_callback)
        return execution_id

    def get_job_status(self, job_id: str) -> Dict[str, Any]:
        future = self.futures.get(job_id)
        if not future:
            return {"status": "unknown"}
            
        if future.running():
            return {"status": "running"}
        elif future.done():
            if future.exception():
                return {"status": "failed", "error": str(future.exception())}
            return {"status": "completed"}
        return {"status": "pending"}
