import supervision as sv

class ByteTrackerWrapper:
    """
    Wrapper for supervision's ByteTrack algorithm.
    It separates tracking logic from detection and application flow.
    """
    
    def __init__(self, track_activation_threshold: float = 0.25, lost_track_buffer: int = 30):
        """
        Initializes the ByteTracker.
        
        Args:
            track_activation_threshold (float): Detection confidence threshold for track activation.
            lost_track_buffer (int): Number of frames to keep a lost track alive before dropping it.
        """
        self.tracker = sv.ByteTrack(
            track_activation_threshold=track_activation_threshold,
            lost_track_buffer=lost_track_buffer
        )
        
    def update(self, detections: sv.Detections) -> sv.Detections:
        """
        Updates the tracker with new detections and assigns persistent track IDs.
        
        Args:
            detections (sv.Detections): The raw detections from the object detector for the current frame.
            
        Returns:
            sv.Detections: Updated detections containing the 'tracker_id' field.
        """
        # Pass detections through ByteTrack to assign IDs
        tracked_detections = self.tracker.update_with_detections(detections=detections)
        return tracked_detections
