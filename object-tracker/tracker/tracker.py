import supervision as sv
from tracker.base import BaseTracker
from core.plugin_manager import plugin_manager

class ByteTrackerPlugin(BaseTracker):
    """
    Wrapper for supervision's ByteTrack algorithm.
    It separates tracking logic from detection and application flow.
    Acts as a tracking plugin.
    """
    
    def __init__(self, track_activation_threshold: float = 0.25, lost_track_buffer: int = 30):
        """
        Initializes the ByteTracker.
        """
        self.tracker = sv.ByteTrack(
            track_activation_threshold=track_activation_threshold,
            lost_track_buffer=lost_track_buffer
        )
        
    @property
    def name(self) -> str:
        return "ByteTrack"

    @property
    def version(self) -> str:
        return "1.0.0"
        
    def update(self, detections: sv.Detections) -> sv.Detections:
        """
        Updates the tracker with new detections and assigns persistent track IDs.
        """
        # Pass detections through ByteTrack to assign IDs
        tracked_detections = self.tracker.update_with_detections(detections=detections)
        return tracked_detections

# Backward compatibility alias
ByteTrackerWrapper = ByteTrackerPlugin

# Register ByteTracker as a plugin
plugin_manager.register_plugin(ByteTrackerPlugin)
