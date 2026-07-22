from typing import List

import numpy as np
import torch

# PyTorch 2.6 compatibility workaround for ultralytics loading weights
_original_load = torch.load


def safe_load(*args, **kwargs):
    if "weights_only" not in kwargs:
        kwargs["weights_only"] = False
    return _original_load(*args, **kwargs)


torch.load = safe_load

import os  # noqa: E402

import supervision as sv  # noqa: E402
from ultralytics import YOLO  # noqa: E402  # Must be imported after safe_load workaround

# Optimize PyTorch CPU threading for CV workloads
if not torch.cuda.is_available():
    import multiprocessing

    cores = max(1, multiprocessing.cpu_count() // 2)
    torch.set_num_threads(cores)

from core.logging import logger  # noqa: E402
from core.models.base import BaseDetector  # noqa: E402
from core.plugin_manager import plugin_manager  # noqa: E402


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
        """Loads the weights into memory, preferring ONNX if available or exporting it."""
        self.device = device
        self.use_half = device == "cuda"

        # Try to use ONNX for CPU inference acceleration
        try:
            # Always load the PyTorch model first to extract metadata
            pt_model = YOLO(
                (
                    self.model_name.replace(".onnx", ".pt")
                    if self.model_name.endswith(".onnx")
                    else self.model_name
                ),
                task="detect",
            )
            # Store names dictionary directly on the detector
            self.names = getattr(pt_model, "names", {})

            onnx_path = self.model_name.replace(".pt", ".onnx")
            if device == "cpu" and self.model_name.endswith(".pt"):
                if not os.path.exists(onnx_path) and os.path.exists(self.model_name):
                    logger.info(f"Exporting {self.model_name} to ONNX for CPU acceleration...")
                    try:
                        pt_model.export(format="onnx", imgsz=640, half=False, simplify=True)
                    except Exception as export_err:
                        logger.warning(
                            f"Failed to export ONNX: {export_err}. Falling back to PyTorch."
                        )

                if os.path.exists(onnx_path):
                    logger.info(f"Attempting to load ONNX model: {onnx_path}")
                    try:
                        self.model = YOLO(onnx_path, task="detect")
                        self.model_name = onnx_path
                    except Exception as onnx_load_err:
                        logger.warning(
                            "Failed to load ONNX model (perhaps missing onnxruntime?): "
                            f"{onnx_load_err}. Falling back to PyTorch model."
                        )
                        self.model = pt_model
                else:
                    self.model = pt_model
            else:
                self.model = YOLO(self.model_name, task="detect")

            if device and not self.model_name.endswith(".onnx"):
                self.model.to(device)
        except Exception as e:
            from core.exceptions import ModelLoadingError

            raise ModelLoadingError(f"Failed to load model {self.model_name}: {str(e)}")

    def detect(
        self, frame: np.ndarray, conf_threshold: float = 0.25, imgsz: int = 640
    ) -> sv.Detections:
        """
        Runs inference on a single frame and returns supervision Detections.
        """
        if self.model is None:
            raise RuntimeError("Model is not loaded. Call load_model() first.")

        # Run inference on the frame under inference_mode for memory/speed gains
        with torch.inference_mode():
            result = self.model(frame, verbose=False, half=self.use_half, imgsz=imgsz)[0]

        # Convert Ultralytics output to supervision Detections format
        detections = sv.Detections.from_ultralytics(result)

        # Filter out low-confidence detections
        detections = detections[detections.confidence >= conf_threshold]

        return detections

    def detect_batch(
        self, frames: List[np.ndarray], conf_threshold: float = 0.25, imgsz: int = 640
    ) -> List[sv.Detections]:
        """
        Runs inference on a batch of frames to maximize GPU throughput.
        """
        if self.model is None:
            raise RuntimeError("Model is not loaded. Call load_model() first.")

        with torch.inference_mode():
            results = self.model(frames, verbose=False, half=self.use_half, imgsz=imgsz)

        batch_detections = []
        for result in results:
            detections = sv.Detections.from_ultralytics(result)
            detections = detections[detections.confidence >= conf_threshold]
            batch_detections.append(detections)

        return batch_detections


# Backward compatibility alias
YoloDetector = YoloDetectorPlugin


class YoloV8nPlugin(YoloDetectorPlugin):
    def __init__(self):
        super().__init__("yolov8n.pt")


class YoloV8sPlugin(YoloDetectorPlugin):
    def __init__(self):
        super().__init__("yolov8s.pt")


class YoloV8mPlugin(YoloDetectorPlugin):
    def __init__(self):
        super().__init__("yolov8m.pt")


plugin_manager.register_plugin(YoloV8nPlugin)
plugin_manager.register_plugin(YoloV8sPlugin)
plugin_manager.register_plugin(YoloV8mPlugin)
