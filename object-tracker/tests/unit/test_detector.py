import pytest
import numpy as np
from tracker.detector import YoloDetector
from core.exceptions import ModelLoadingError
from unittest.mock import patch, MagicMock

@pytest.fixture
def mock_yolo_model():
    with patch("tracker.detector.YOLO") as MockYOLO:
        mock_instance = MagicMock()
        mock_instance.names = {0: "person", 2: "car"}
        
        # Mock the predict method to return a dummy result
        mock_result = MagicMock()
        mock_box = MagicMock()
        mock_box.xyxy = np.array([[10, 10, 50, 50]])
        mock_box.conf = np.array([0.9])
        mock_box.cls = np.array([0])
        mock_result.boxes = mock_box
        
        mock_instance.predict.return_value = [mock_result]
        MockYOLO.return_value = mock_instance
        yield MockYOLO

def test_yolo_detector_initialization(mock_yolo_model):
    detector = YoloDetector("dummy_path.pt")
    mock_yolo_model.assert_called_once_with("dummy_path.pt")
    assert detector.model.names[0] == "person"

def test_yolo_detector_invalid_path():
    with pytest.raises(ModelLoadingError):
        YoloDetector("non_existent_path.pt")

def test_yolo_detector_inference(mock_yolo_model):
    detector = YoloDetector("dummy_path.pt")
    dummy_frame = np.zeros((100, 100, 3), dtype=np.uint8)
    
    detections = detector.detect(dummy_frame)
    
    # Verify supervision Detections object is constructed
    assert len(detections) == 1
    assert detections.class_id[0] == 0
    assert detections.confidence[0] == 0.9
    np.testing.assert_array_equal(detections.xyxy[0], [10, 10, 50, 50])
