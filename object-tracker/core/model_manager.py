import threading
import torch
from typing import Dict, Any, Optional
from core.logging import logger
from tracker.detector import YoloDetector

class ModelManager:
    """
    Manages the lifecycle of models (e.g. YOLOv8) to ensure thread-safe, 
    singleton-like behavior and handles hardware acceleration assignment.
    """
    
    def __init__(self):
        self._models: Dict[str, Any] = {}
        self._lock = threading.Lock()
        self.device = self._detect_device()

    def _detect_device(self) -> str:
        """Automatically detects the best available hardware for PyTorch."""
        if torch.cuda.is_available():
            logger.info("Hardware acceleration detected: CUDA")
            return "cuda"
        elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            logger.info("Hardware acceleration detected: Apple MPS")
            return "mps"
        else:
            logger.info("No hardware acceleration detected. Using CPU.")
            return "cpu"

    def get_yolo_model(self, model_path: str) -> YoloDetector:
        """
        Retrieves a cached YOLO model or loads it if it doesn't exist.
        """
        with self._lock:
            if model_path not in self._models:
                logger.info(f"Loading YOLO model into memory: {model_path} on {self.device}")
                # We initialize YoloDetector (which wraps YOLO) here.
                # The YOLO object inside can be moved to the correct device if not auto-handled.
                detector = YoloDetector(model_name=model_path, device=self.device)
                self._models[model_path] = detector
            return self._models[model_path]

    def get_loaded_models_info(self) -> Dict[str, str]:
        """Returns info on currently loaded models."""
        with self._lock:
            return {
                path: "loaded" for path in self._models.keys()
            }
