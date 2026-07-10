# Trackr Plugin SDK Guide

Trackr was built with extensibility in mind. The Plugin SDK allows you to create custom AI models, specialized tracking algorithms, advanced analytics logic, and data export sinks without modifying the core Trackr repository.

## Plugin Types

Trackr supports the following types of plugins, all inheriting from `BasePlugin` (found in `core/plugin_manager.py`):

1. **Detection Plugins (`BaseDetector`)**: Introduce new object detection architectures (e.g., YOLOv9, RT-DETR, custom classifiers).
2. **Tracking Plugins (`BaseTracker`)**: Implement specific multi-object tracking (MOT) logic (e.g., DeepSORT, BoT-SORT, custom logic).
3. **Analytics Plugins (`BaseAnalytics`)**: Build advanced processing modules such as Heatmaps, Loitering detection, and Zone transitions.

## Creating a Plugin

### 1. Scaffold the Plugin

A plugin should be a standard Python class that inherits from the correct Base class.

```python
from core.models.base import BaseDetector
from core.plugin_manager import plugin_manager
import supervision as sv
import numpy as np

class MyCustomDetector(BaseDetector):
    @property
    def name(self) -> str:
        return "MyCustomDetector"
        
    @property
    def version(self) -> str:
        return "1.0.0"
        
    def load(self, model_path: str, **kwargs):
        # Initialize your PyTorch/ONNX/TensorRT model here
        self.model = ...
        
    def predict(self, frame: np.ndarray, **kwargs) -> sv.Detections:
        # Run inference and map output to a supervision.Detections object
        return sv.Detections(...)

# Auto-register when this module is imported
plugin_manager.register_plugin(MyCustomDetector)
```

### 2. Register the Plugin

You can register your plugin in two ways:

- **Implicitly:** Place your Python file inside the `plugins/` directory of your Trackr deployment. Trackr automatically discovers and loads all `.py` files in this directory on startup.
- **Programmatically:** Call `plugin_manager.register_plugin(MyClass)` from your own main entry point before launching the API.

## Best Practices

- Always return `supervision.Detections` for detection plugins to ensure compatibility with downstream trackers and analytics.
- Use `logger` from `core.logging` for consistent output formatting.
- Do not block the main thread. If your plugin performs heavy disk I/O (like an Export plugin), offload the work using `asyncio` or a background thread.
