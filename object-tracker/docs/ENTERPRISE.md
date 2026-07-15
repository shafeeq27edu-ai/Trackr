# Trackr Enterprise Architecture Guide

This document describes the enterprise-grade architecture of the Trackr platform, including its plugin system, model registry, event bus, storage abstraction, and distributed processing readiness.

## 1. Plugin System

Trackr supports a dynamic plugin system to extend its capabilities without modifying the core codebase. Plugins can fall into several categories:
- **Detection Plugins**: Provide new object detection models (e.g., YOLOv11, RT-DETR).
- **Tracking Plugins**: Provide new tracking algorithms (e.g., DeepSORT, BoT-SORT).
- **Analytics Plugins**: Provide custom business logic and analytics on top of object detections (e.g., Heatmaps, Dwell Time).

### Creating a Plugin

To create a plugin, inherit from one of the base plugin classes and implement the required abstract methods. Place your plugin in the `plugins/` directory or register it programmatically.

```python
from core.plugin_manager import BasePlugin, plugin_manager

class MyCustomPlugin(BasePlugin):
    @property
    def name(self) -> str:
        return "MyCustomPlugin"

    @property
    def version(self) -> str:
        return "1.0.0"
        
    @property
    def category(self) -> str:
        return "custom"

# Register the plugin
plugin_manager.register_plugin(MyCustomPlugin)
```

## 2. Model Registry

The Model Registry centralizes the lifecycle management of AI models. It handles discovery, lazy loading, and caching.

```python
from core.models.registry import model_registry

# Load a model dynamically
detector = model_registry.get_model("yolov8s.pt")
```

## 3. Event System

Trackr features an in-memory event bus (`EventBus`) for decoupled communication between components. Plugins can subscribe to standard system events.

### Standard Events
- `JobCreated`
- `JobStarted`
- `JobCompleted`
- `JobFailed`
- `PluginLoaded`
- `ModelLoaded`

### Subscribing to Events

```python
from core.events import event_bus, EventType

def on_job_completed(payload):
    print(f"Job completed: {payload['job_id']}")

event_bus.subscribe(EventType.JOB_COMPLETED, on_job_completed)
```

## 4. Storage Providers

Storage operations (like saving processed videos) are abstracted behind the `StorageProvider` interface. Currently, `LocalStorageProvider` is implemented, but you can extend this for cloud storage (AWS S3, Google Cloud Storage, Azure Blob).

The configured provider can be accessed via `storage_manager.get_provider()`.

## 5. Distributed Execution

Background job execution is abstracted through the `ExecutionBackend` interface. `CeleryExecutionBackend` dispatches tasks to a Celery worker pool backed by Redis. The interface can be extended to support Ray, Kubernetes Jobs, or other distributed task runners.

## 6. Enterprise Configuration

Trackr supports environment-specific configuration profiles via Pydantic settings. Set the `ENVIRONMENT` variable (e.g., `development`, `production`) to automatically load overrides from `.env.production`.
