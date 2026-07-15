import numpy as np
import supervision as sv
from abc import abstractmethod

from core.plugin_manager import BasePlugin


class BaseDetector(BasePlugin):
    """Base class for all object detection models."""

    @property
    def category(self) -> str:
        return "detection"

    @abstractmethod
    def load_model(self, device: str = "cpu"):
        """Loads the model into memory on the specified device."""
        pass

    @abstractmethod
    def detect(self, frame: np.ndarray, conf_threshold: float = 0.25) -> sv.Detections:
        """Runs inference on a single frame and returns supervision Detections."""
        pass
