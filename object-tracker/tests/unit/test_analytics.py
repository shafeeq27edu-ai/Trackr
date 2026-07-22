import os
import shutil

import numpy as np
import pytest
import supervision as sv

from tracker.analytics import AnalyticsEngine


@pytest.fixture
def analytics():
    # Use a safe test directory
    test_dir = "tests/test_outputs/analytics_test"
    os.makedirs(test_dir, exist_ok=True)
    engine = AnalyticsEngine(log_dir=test_dir, fps=30.0)
    yield engine
    shutil.rmtree(test_dir, ignore_errors=True)


def test_process_detections_counts_unique(analytics):
    class_names = {0: "person", 1: "car"}

    # Frame 1: Person (ID 1), Car (ID 2)
    det1 = sv.Detections(
        xyxy=np.array([[0, 0, 10, 10], [20, 20, 30, 30]]),
        class_id=np.array([0, 1]),
        confidence=np.array([0.9, 0.9]),
        tracker_id=np.array([1, 2]),
    )
    analytics.process_detections(det1, class_names, frame_idx=0)

    # Frame 2: Person (ID 1) again
    det2 = sv.Detections(
        xyxy=np.array([[5, 5, 15, 15]]),
        class_id=np.array([0]),
        confidence=np.array([0.9]),
        tracker_id=np.array([1]),
    )
    analytics.process_detections(det2, class_names, frame_idx=1)

    # Unique counts should be 1 person, 1 car
    assert len(analytics.unique_counts["person"]) == 1
    assert len(analytics.unique_counts["car"]) == 1

    # Dwell time for person (ID 1) should span from frame 0 to 1
    assert analytics.dwell_times[1]["first"] == 0
    assert analytics.dwell_times[1]["last"] == 1


def test_zone_triggers(analytics):
    analytics.register_zone("zone_A")

    # Frame 1: ID 1 enters zone A
    analytics.process_zone_triggers("zone_A", trigger_results=[True], tracker_ids=[1])
    assert analytics.zone_stats["zone_A"]["entries"] == 1
    assert analytics.zone_stats["zone_A"]["exits"] == 0

    # Frame 2: ID 1 stays in zone A
    analytics.process_zone_triggers("zone_A", trigger_results=[True], tracker_ids=[1])
    assert analytics.zone_stats["zone_A"]["entries"] == 1
    assert analytics.zone_stats["zone_A"]["exits"] == 0

    # Frame 3: ID 1 leaves zone A
    analytics.process_zone_triggers("zone_A", trigger_results=[False], tracker_ids=[1])
    assert analytics.zone_stats["zone_A"]["entries"] == 1
    assert analytics.zone_stats["zone_A"]["exits"] == 1


def test_generate_session_summary(analytics):
    class_names = {0: "person"}
    det = sv.Detections(
        xyxy=np.array([[0, 0, 10, 10]]),
        class_id=np.array([0]),
        confidence=np.array([0.9]),
        tracker_id=np.array([99]),
    )

    analytics.process_detections(det, class_names, frame_idx=0)
    analytics.process_detections(det, class_names, frame_idx=30)  # 1 second later at 30fps

    summary = analytics.generate_session_summary(total_frames=100, duration_sec=5.0)

    assert summary["video_stats"]["total_frames"] == 100
    assert summary["traffic_stats"]["total_unique_objects"] == 1
    assert summary["class_distribution"]["person"] == 1
    # 30 frames at 30 fps = 1.0 second dwell time
    assert summary["dwell_times_sec"]["maximum"] == 1.0


def test_speed_and_direction(analytics):
    class_names = {0: "car"}

    # Simulate an object moving East (x increases) over 5 frames
    for i in range(5):
        det = sv.Detections(
            xyxy=np.array([[i * 10, 0, i * 10 + 10, 10]]),  # moves by 10 pixels per frame
            class_id=np.array([0]),
            confidence=np.array([0.9]),
            tracker_id=np.array([1]),
        )
        analytics.process_detections(det, class_names, frame_idx=i)

    speed = analytics.get_track_speed(1)
    direction = analytics.get_track_direction(1)

    # 4 frames elapsed between index 0 and 4.
    # dt = 4 / 30.0 = 0.133333 seconds
    # dx = 40 pixels. distance = 40 pixels * 0.05 meters/pixel = 2.0 meters.
    # speed = 2.0 / (4 / 30) = 15.0 m/s = 54.0 km/h.
    assert abs(speed - 54.0) < 0.1
    assert direction == "East"

    # Check that summary has speed stats
    summary = analytics.generate_session_summary(total_frames=5, duration_sec=0.16)
    assert "speed_stats" in summary
    assert summary["speed_stats"]["average_speed_kmh"] == round(speed, 2)
    assert summary["speed_stats"]["class_averages_kmh"]["car"] == round(speed, 2)
