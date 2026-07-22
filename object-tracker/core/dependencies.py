from config.settings import Settings, get_cached_settings
from core.job_manager import JobManager
from core.model_manager import ModelManager
from core.stream_manager import StreamManager
from tracker.detector import YoloDetector

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


_job_service_instance = None


def get_job_service() -> "JobService":  # type: ignore  # noqa: F821

    global _job_service_instance
    if _job_service_instance is not None:
        return _job_service_instance

    from services.job_service import JobService

    settings = get_cached_settings()

    # We only initialize this once per worker, could be made a global singleton too.
    global _execution_backend
    if "_execution_backend" not in globals():
        if settings.execution_backend == "celery":
            from core.execution.celery_backend import CeleryExecutionBackend
            from core.execution.worker import celery_app

            _execution_backend = CeleryExecutionBackend(celery_app)
        elif settings.execution_backend == "local":
            from core.execution.local_backend import LocalExecutionBackend

            _execution_backend = LocalExecutionBackend()
        else:
            raise ValueError(f"Unsupported execution_backend: {settings.execution_backend}")

    _job_service_instance = JobService(
        job_manager=_job_manager,
        settings=settings,
        detector=get_detector(),
        execution_backend=_execution_backend,
    )
    return _job_service_instance
