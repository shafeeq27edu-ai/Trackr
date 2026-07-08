from fastapi import Request
from config.settings import Settings
from tracker.detector import YoloDetector

def get_settings(request: Request) -> Settings:
    """Dependency to inject the application settings."""
    return request.app.state.settings

def get_detector(request: Request) -> YoloDetector:
    """Dependency to inject the pre-loaded YOLO detector."""
    return request.app.state.detector
