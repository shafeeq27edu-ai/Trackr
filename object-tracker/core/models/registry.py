import threading
import torch
from typing import Dict, List, Any, Optional, Type
import logging

from core.models.base import BaseDetector
from core.events import event_bus, EventType
from core.plugin_manager import plugin_manager

logger = logging.getLogger(__name__)

class ModelRegistry:
    """
    Centralized registry for managing AI models.
    Handles discovery, lazy loading, caching, and hardware acceleration assignment.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ModelRegistry, cls).__new__(cls)
            cls._instance._models: Dict[str, BaseDetector] = {}
            cls._instance._loaded_instances: Dict[str, BaseDetector] = {}
            cls._instance._lock = threading.Lock()
            cls._instance.device = cls._instance._detect_device()
        return cls._instance

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

    def register_model(self, model_id: str, model_class: Type[BaseDetector]):
        """Registers a model class with a specific ID."""
        with self._lock:
            # We instantiate it but don't load the heavy weights yet.
            if model_id not in self._models:
                instance = model_class()
                self._models[model_id] = instance
                logger.info(f"Registered model in registry: {model_id} (v{instance.version})")

    def discover_from_plugins(self):
        """Finds all detection plugins and registers them as models."""
        detectors = plugin_manager.get_plugins_by_category("detection")
        for detector in detectors:
            # Register by name
            self._models[detector.name] = detector

    def get_model(self, model_id: str) -> BaseDetector:
        """
        Retrieves a loaded model, loading it if necessary.
        """
        with self._lock:
            if model_id not in self._models:
                # If not explicitly registered, we could try to instantiate a generic YOLO fallback,
                # but it's better to explicitly register models. 
                # For backward compatibility, we can assume YOLOv8 if it ends in .pt
                if model_id.endswith(".pt"):
                    logger.info(f"Dynamically registering {model_id} as a YOLO model.")
                    # We need to import YoloDetector here to avoid circular imports
                    from tracker.detector import YoloDetectorPlugin
                    instance = YoloDetectorPlugin(model_name=model_id)
                    self._models[model_id] = instance
                else:
                    raise ValueError(f"Model {model_id} is not registered in the ModelRegistry.")

            if model_id not in self._loaded_instances:
                logger.info(f"Loading model into memory: {model_id} on {self.device}")
                instance = self._models[model_id]
                instance.load_model(device=self.device)
                self._loaded_instances[model_id] = instance
                event_bus.publish(EventType.MODEL_LOADED, {"model_id": model_id, "device": self.device})

            return self._loaded_instances[model_id]

    def get_available_models(self) -> List[Dict[str, Any]]:
        """Returns info on all registered models."""
        with self._lock:
            return [
                {
                    "id": model_id,
                    "name": model.name,
                    "version": model.version,
                    "is_loaded": model_id in self._loaded_instances
                }
                for model_id, model in self._models.items()
            ]

# Global registry instance
model_registry = ModelRegistry()
