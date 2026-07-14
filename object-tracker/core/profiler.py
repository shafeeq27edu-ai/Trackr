import time
from contextlib import contextmanager
from typing import Dict, List
import threading
from core.logging import logger

class Profiler:
    def __init__(self):
        self.metrics: Dict[str, List[float]] = {}
        self.lock = threading.Lock()

    @contextmanager
    def measure(self, name: str):
        start = time.perf_counter()
        yield
        elapsed = time.perf_counter() - start
        with self.lock:
            if name not in self.metrics:
                self.metrics[name] = []
            self.metrics[name].append(elapsed)
            # Keep only the last 100 measurements for rolling average
            if len(self.metrics[name]) > 100:
                self.metrics[name].pop(0)

    def get_averages(self) -> Dict[str, float]:
        with self.lock:
            return {
                name: sum(times) / len(times) if times else 0.0
                for name, times in self.metrics.items()
            }
            
    def get_summary_string(self) -> str:
        avgs = self.get_averages()
        return " | ".join(f"{name}: {avg*1000:.1f}ms" for name, avg in avgs.items())
        
    def reset(self):
        with self.lock:
            self.metrics.clear()

# Global instance for easy import
system_profiler = Profiler()
