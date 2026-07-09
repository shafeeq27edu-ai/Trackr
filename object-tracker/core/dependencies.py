from fastapi import Request
from config.settings import Settings
from tracker.detector import YoloDetector
from core.job_manager import JobManager

def get_settings(request: Request) -> Settings:
    """Dependency to inject the application settings."""
    return request.app.state.settings

def get_detector(request: Request) -> YoloDetector:
    """Dependency to inject the pre-loaded YOLO detector from ModelManager."""
    model_manager = request.app.state.model_manager
    return model_manager.get_yolo_model(request.app.state.settings.yolo_model_path)

def get_model_manager(request: Request):
    """Dependency to inject the ModelManager."""
    return request.app.state.model_manager

def get_job_manager(request: Request) -> JobManager:
    """Dependency to inject the global JobManager."""
    return request.app.state.job_manager

def get_stream_manager(request: Request):
    """Dependency to inject the global StreamManager."""
    return request.app.state.stream_manager
