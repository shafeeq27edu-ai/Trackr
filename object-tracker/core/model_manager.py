import threading
import torch
from typing import Dict, Any, Optional
from core.logging import logger
from tracker.detector import YoloDetector
from core.models.registry import model_registry

class ModelManager:
    """
    Manages the lifecycle of models (e.g. YOLOv8).
    Maintained for backward compatibility. Defers to ModelRegistry.
    """
    
    def __init__(self):
        # We don't need to maintain our own models dict anymore
        self.device = model_registry.device

    def get_yolo_model(self, model_path: str) -> YoloDetector:
        """
        Retrieves a cached YOLO model or loads it if it doesn't exist.
        Delegates to the model_registry.
        """
        # Model registry handles loading and caching
        return model_registry.get_model(model_path)

    def get_loaded_models_info(self) -> Dict[str, str]:
        """Returns info on currently loaded models."""
        models = model_registry.get_available_models()
        return {
            m["id"]: "loaded" for m in models if m["is_loaded"]
        }
