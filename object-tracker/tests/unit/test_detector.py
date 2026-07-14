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
        
        mock_xyxy = MagicMock()
        mock_xyxy.cpu.return_value.numpy.return_value = np.array([[10, 10, 50, 50]])
        mock_box.xyxy = mock_xyxy
        
        mock_conf = MagicMock()
        mock_conf.cpu.return_value.numpy.return_value = np.array([0.9])
        mock_box.conf = mock_conf
        
        mock_cls = MagicMock()
        mock_cls.cpu.return_value.numpy.return_value = np.array([0])
        mock_box.cls = mock_cls
        
        mock_box.id = None
        mock_result.boxes = mock_box
        mock_result.masks = None
        
        mock_instance.predict.return_value = [mock_result]
        mock_instance.return_value = [mock_result]
        MockYOLO.return_value = mock_instance
        yield MockYOLO

def test_yolo_detector_initialization(mock_yolo_model):
    detector = YoloDetector("dummy_path.pt")
    detector.load_model()
    mock_yolo_model.assert_called_once_with("dummy_path.pt", task='detect')
    assert detector.model.names[0] == "person"

def test_yolo_detector_invalid_path():
    detector = YoloDetector("non_existent_path.pt")
    with pytest.raises(ModelLoadingError):
        detector.load_model()

def test_yolo_detector_inference(mock_yolo_model):
    detector = YoloDetector("dummy_path.pt")
    detector.load_model()
    dummy_frame = np.zeros((100, 100, 3), dtype=np.uint8)
    
    detections = detector.detect(dummy_frame)
    
    # Verify supervision Detections object is constructed
    assert len(detections) == 1
    assert detections.class_id[0] == 0
    assert detections.confidence[0] == 0.9
    np.testing.assert_array_equal(detections.xyxy[0], [10, 10, 50, 50])
