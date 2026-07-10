# Model Registry — Trackr v1.0

To maintain a low VRAM profile, Trackr implements a lazy-loading Model Registry pattern that loads model weights into memory only on demand.

---

## 1. lazy Loading Mechanism

When the backend API server boots, it registers available models without loading their weights (tensors) into VRAM:
1. **Discovery**: Plugins register model paths during startup.
2. **First Call**: When a video processing job starts, the `ModelRegistry` checks if the requested model is in memory.
3. **Loading**: If not, it instantiates the model weights on the target device (`cuda`, `mps`, or `cpu`) and caches the instance.
4. **Subsequent Calls**: Future jobs querying the same model reuse the cached in-memory instance, avoiding VRAM overhead and model loading latency.

---

## 2. Configuration Settings

Model settings are configured via environment variables:
* **`YOLO_MODEL_PATH`**: Defaults to `yolov8n.pt`.
* **`HARDWARE_ACCELERATION`**: Set to `cuda` (NVIDIA GPUs), `mps` (Apple Silicon), or `cpu` (Default fallback).

---

## 3. Registering Custom Model Plugins

To add a new YOLO version or custom weights:
1. Create a script or add inside `tracker/detector.py`:
   ```python
   from core.plugin_manager import plugin_manager
   from tracker.detector import YoloDetectorPlugin

   # Register a new custom model configuration
   plugin_manager.register_plugin(lambda: YoloDetectorPlugin("my_custom_weights.pt"))
   ```
2. The model will automatically show up in `GET /api/v1/system/models` and will lazy-load when queried.
