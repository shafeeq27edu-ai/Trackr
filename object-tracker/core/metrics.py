from typing import Any, Dict

import psutil
import torch


class SystemMetrics:
    @staticmethod
    def get_cpu_usage() -> float:
        return psutil.cpu_percent(interval=None)

    @staticmethod
    def get_memory_usage() -> Dict[str, Any]:
        mem = psutil.virtual_memory()
        return {
            "total_gb": round(mem.total / (1024**3), 2),
            "used_gb": round(mem.used / (1024**3), 2),
            "percent": mem.percent,
        }

    @staticmethod
    def get_gpu_usage() -> Dict[str, Any]:
        """Gets GPU usage if available via PyTorch."""
        if torch.cuda.is_available():
            device = torch.cuda.current_device()
            return {
                "type": "cuda",
                "name": torch.cuda.get_device_name(device),
                "memory_allocated_gb": round(torch.cuda.memory_allocated(device) / (1024**3), 2),
                "memory_reserved_gb": round(torch.cuda.memory_reserved(device) / (1024**3), 2),
            }
        elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            return {"type": "mps", "name": "Apple Silicon GPU (MPS)"}
        return {"type": "cpu"}

    @staticmethod
    def get_all_metrics() -> Dict[str, Any]:
        return {
            "cpu_percent": SystemMetrics.get_cpu_usage(),
            "memory": SystemMetrics.get_memory_usage(),
            "gpu": SystemMetrics.get_gpu_usage(),
        }
