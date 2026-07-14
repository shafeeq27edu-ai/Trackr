from fastapi import APIRouter, Depends
from core.metrics import SystemMetrics
from core.dependencies import get_model_manager, get_job_manager
from core.model_manager import ModelManager
from core.job_manager import JobManager, JobStatus

router = APIRouter()

@router.get("/performance")
async def get_performance_metrics(job_manager: JobManager = Depends(get_job_manager)):
    """Returns general performance metrics like processing throughput and active jobs."""
    jobs = await job_manager.get_all_jobs()
    active_jobs = [j for j in jobs.values() if j.status in [JobStatus.INITIALIZING, JobStatus.PROCESSING]]
    
    return {
        "active_jobs_count": len(active_jobs),
        "total_jobs_count": len(jobs),
        "queue_length": sum(1 for j in jobs.values() if j.status == JobStatus.QUEUED)
    }

@router.get("/diagnostics")
async def get_diagnostics(job_manager: JobManager = Depends(get_job_manager)):
    """Detailed system and streaming diagnostics."""
    from core.stream_manager import stream_manager
    from core.profiler import system_profiler
    
    active_streams = stream_manager.get_active_streams()
    
    all_jobs = await job_manager.get_all_jobs()
    
    # Calculate global tracking FPS across all running streams and jobs
    stream_fps = sum(s.fps for s in active_streams)
    job_fps = sum(j.average_fps for j in all_jobs.values() if j.average_fps)
    global_fps = stream_fps + job_fps
    
    return {
        "profiler": system_profiler.get_averages(),
        "streams": {
            "active_count": len(active_streams),
            "websocket_clients": len(stream_manager.active_connections),
            "global_fps": global_fps
        },
        "resources": SystemMetrics.get_all_metrics(),
        "jobs": {
            "queued": len([j for j in all_jobs.values() if j.status == JobStatus.QUEUED]),
            "active": len([j for j in all_jobs.values() if j.status == JobStatus.PROCESSING])
        }
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
