from fastapi import APIRouter, Depends
from core.metrics import SystemMetrics
from core.dependencies import get_model_manager, get_job_manager
from core.model_manager import ModelManager
from core.job_manager import JobManager, JobStatus

router = APIRouter()

@router.get("/performance")
def get_performance_metrics(job_manager: JobManager = Depends(get_job_manager)):
    """Returns general performance metrics like processing throughput and active jobs."""
    jobs = job_manager.get_all_jobs()
    active_jobs = [j for j in jobs.values() if j.status in [JobStatus.INITIALIZING, JobStatus.PROCESSING]]
    
    return {
        "active_jobs_count": len(active_jobs),
        "total_jobs_count": len(jobs),
        "queue_length": sum(1 for j in jobs.values() if j.status == JobStatus.QUEUED)
    }

@router.get("/resources")
def get_resource_metrics():
    """Returns CPU, Memory, and GPU usage metrics."""
    return SystemMetrics.get_all_metrics()

@router.get("/models")
def get_loaded_models(model_manager: ModelManager = Depends(get_model_manager)):
    """Returns information about loaded AI models and hardware."""
    return {
        "device": model_manager.device,
        "loaded_models": model_manager.get_loaded_models_info()
    }
