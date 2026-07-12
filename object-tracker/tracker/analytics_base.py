from typing import Dict, Any, List
import supervision as sv
from abc import abstractmethod

from core.plugin_manager import BasePlugin

class BaseAnalytics(BasePlugin):
    """Base class for all analytics modules."""

    @property
    def category(self) -> str:
        return "analytics"

    @abstractmethod
    def process_frame(self, detections: sv.Detections, *args, **kwargs) -> None:
        """Process a single frame's detections."""
        pass
        
    @abstractmethod
    def get_results(self) -> Dict[str, Any]:
        """Return the aggregated analytics results."""
        pass
        
    def reset(self) -> None:
        """Reset the analytics state (useful for multi-video processing without re-instantiation)."""
        pass
