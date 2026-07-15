import supervision as sv
from abc import abstractmethod

from core.plugin_manager import BasePlugin


class BaseTracker(BasePlugin):
    """Base class for all tracking algorithms."""

    @property
    def category(self) -> str:
        return "tracking"

    @abstractmethod
    def update(self, detections: sv.Detections) -> sv.Detections:
        """
        Updates the tracker with new detections and assigns persistent track IDs.
        """
        pass
