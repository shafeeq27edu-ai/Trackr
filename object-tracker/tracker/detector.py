import numpy as np
import torch

# Fix for PyTorch 2.6+ weights_only=True default breaking older ultralytics
original_load = torch.load
def safe_load(*args, **kwargs):
    kwargs.setdefault('weights_only', False)
    return original_load(*args, **kwargs)
torch.load = safe_load

from ultralytics import YOLO
import supervision as sv

from core.models.base import BaseDetector
from core.plugin_manager import plugin_manager

class YoloDetectorPlugin(BaseDetector):
    """
    Wrapper for YOLOv8 inference that standardizes outputs into supervision.Detections.
    Acts as a detection plugin for the ModelRegistry.
    """
    
    def __init__(self, model_name: str = "yolov8n.pt"):
        """
        Initializes the YOLOv8 model plugin definition.
        """
        self.model_name = model_name
        self.model = None
        self.device = None
        
    @property
    def name(self) -> str:
        return f"YOLOv8 ({self.model_name})"

    @property
    def version(self) -> str:
        return "1.0.0"
        
    def load_model(self, device: str = "cpu"):
        """Loads the weights into memory."""
        self.device = device
        self.use_half = device == "cuda"
        try:
            self.model = YOLO(self.model_name)
            if device:
                self.model.to(device)
        except Exception as e:
            from core.exceptions import ModelLoadingError
            raise ModelLoadingError(f"Failed to load model {self.model_name}: {str(e)}")
    
    def detect(self, frame: np.ndarray, conf_threshold: float = 0.25) -> sv.Detections:
        """
        Runs inference on a single frame and returns supervision Detections.
        """
        if self.model is None:
            raise RuntimeError("Model is not loaded. Call load_model() first.")
            
        # Run inference on the frame under inference_mode for memory/speed gains
        with torch.inference_mode():
            result = self.model(frame, verbose=False, half=self.use_half)[0]
        
        # Convert Ultralytics output to supervision Detections format
        detections = sv.Detections.from_ultralytics(result)
        
        # Filter out low-confidence detections
        detections = detections[detections.confidence >= conf_threshold]
        
        return detections

# Backward compatibility alias
YoloDetector = YoloDetectorPlugin

# Register common YOLO models as plugins
plugin_manager.register_plugin(lambda: YoloDetectorPlugin("yolov8n.pt"))
plugin_manager.register_plugin(lambda: YoloDetectorPlugin("yolov8s.pt"))
plugin_manager.register_plugin(lambda: YoloDetectorPlugin("yolov8m.pt"))
