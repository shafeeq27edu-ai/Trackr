from abc import ABC, abstractmethod
from typing import Callable, Any, Dict

class ExecutionBackend(ABC):
    """Abstract base class for distributed task execution."""

    @abstractmethod
    def submit_job(self, task: Callable, *args, **kwargs) -> str:
        """Submits a job to the execution backend and returns a tracking ID."""
        pass

    @abstractmethod
    def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """Retrieves the status of a submitted job."""
        pass
