import numpy as np
import torch
import functools

# Fix for PyTorch 2.6+ weights_only=True default breaking older ultralytics
original_load = torch.load
def safe_load(*args, **kwargs):
    kwargs.setdefault('weights_only', False)
    return original_load(*args, **kwargs)
torch.load = safe_load

from ultralytics import YOLO
import supervision as sv

class YoloDetector:
    """
    Wrapper for YOLOv8 inference that standardizes outputs into supervision.Detections.
    """
    
    def __init__(self, model_name: str = "yolov8n.pt", device: str = None):
        """
        Initializes the YOLOv8 model.
        
        Args:
            model_name (str): The name or path of the YOLO model weights.
            device (str): Device to run the model on (e.g. 'cpu', 'cuda', 'mps').
        """
        self.model = YOLO(model_name)
        if device:
            self.model.to(device)
    
    def detect(self, frame: np.ndarray, conf_threshold: float = 0.25) -> sv.Detections:
        """
        Runs inference on a single frame and returns supervision Detections.
        
        Args:
            frame (np.ndarray): The input image/frame.
            conf_threshold (float): Minimum confidence to keep a detection.
            
        Returns:
            sv.Detections: The detected objects.
        """
        # Run inference on the frame
        result = self.model(frame, verbose=False)[0]
        
        # Convert Ultralytics output to supervision Detections format
        detections = sv.Detections.from_ultralytics(result)
        
        # Filter out low-confidence detections
        detections = detections[detections.confidence >= conf_threshold]
        
        return detections
