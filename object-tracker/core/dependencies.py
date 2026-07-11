from fastapi import Request
from config.settings import Settings, get_cached_settings
from tracker.detector import YoloDetector
from core.job_manager import JobManager
from core.model_manager import ModelManager
from core.stream_manager import StreamManager

# Global singleton instances for dependencies
_job_manager = JobManager()
_stream_manager = StreamManager()
_model_manager = ModelManager()

def get_settings() -> Settings:
    """Dependency to inject the application settings."""
    return get_cached_settings()

def get_model_manager() -> ModelManager:
    """Dependency to inject the global ModelManager."""
    return _model_manager

def get_detector() -> YoloDetector:
    """Dependency to inject the pre-loaded YOLO detector from ModelManager."""
    settings = get_cached_settings()
    return _model_manager.get_yolo_model(settings.yolo_model_path)

def get_job_manager() -> JobManager:
    """Dependency to inject the global JobManager."""
    return _job_manager

def get_stream_manager() -> StreamManager:
    """Dependency to inject the global StreamManager."""
    return _stream_manager

def get_job_service() -> "JobService":
    """Dependency to inject the JobService."""
    from services.job_service import JobService
    return JobService(
        job_manager=_job_manager,
        settings=get_cached_settings(),
        detector=get_detector()
    )
