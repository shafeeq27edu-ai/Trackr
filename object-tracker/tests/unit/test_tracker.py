import pytest
import numpy as np
import supervision as sv
from tracker.tracker import ByteTrackerWrapper


def test_bytetrack_initialization():
    tracker = ByteTrackerWrapper()
    assert tracker.tracker is not None


def test_bytetrack_update_with_detections():
    tracker = ByteTrackerWrapper()

    # Create mock detections
    xyxy = np.array([[100, 100, 200, 200]])
    confidence = np.array([0.85])
    class_id = np.array([0])
    detections = sv.Detections(xyxy=xyxy, confidence=confidence, class_id=class_id)

    tracked_detections = tracker.update(detections)

    # The first frame a detection is seen, ByteTrack should assign it an ID
    assert len(tracked_detections) == 1
    assert tracked_detections.tracker_id is not None
    assert len(tracked_detections.tracker_id) == 1


def test_bytetrack_empty_detections():
    tracker = ByteTrackerWrapper()
    empty_detections = sv.Detections.empty()

    tracked_detections = tracker.update(empty_detections)
    assert len(tracked_detections) == 0
