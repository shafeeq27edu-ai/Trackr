import pytest
import asyncio
import numpy as np
from unittest.mock import MagicMock, AsyncMock, patch
import supervision as sv
from core.stream_manager import StreamManager, StreamStatus
from services.stream_service import process_live_stream


@pytest.mark.anyio
async def test_process_live_stream():
    stream_manager = StreamManager()
    stream = stream_manager.create_stream(source="mock_cam")
    stream.stop_event = asyncio.Event()

    # Create mock frame
    mock_frame = np.zeros((240, 320, 3), dtype=np.uint8)

    # Mock cv2 VideoCapture
    mock_cap = MagicMock()
    mock_cap.isOpened.return_value = True

    # Return true for frame reads
    def mock_read():
        return True, mock_frame

    mock_cap.read.side_effect = mock_read
    mock_cap.get.return_value = 30.0

    # Mock detector
    mock_detector = MagicMock()
    mock_detector.model.names = {0: "person"}
    mock_detector.detect.return_value = sv.Detections.empty()

    # Mock broadcast to stream as AsyncMock
    broadcast_mock = AsyncMock()
    stream_manager.broadcast_bytes_to_stream = broadcast_mock

    with (
        patch("cv2.VideoCapture", return_value=mock_cap),
        patch("cv2.imencode", return_value=(True, np.array([1, 2, 3]))),
    ):

        # Schedule stopping the stream after the loop starts
        async def stop_soon():
            await asyncio.sleep(0.05)
            stream.stop_event.set()

        asyncio.create_task(stop_soon())

        # Run process loop in task or await directly since it halts when stop_event is set
        await process_live_stream(stream.id, "mock_cam", stream_manager, mock_detector)

    # Assertions
    assert stream.status == StreamStatus.STOPPED
    mock_cap.release.assert_called_once()
    assert broadcast_mock.call_count >= 1

    # Check broadcast message format
    broadcast_args = broadcast_mock.call_args[0]
    assert broadcast_args[0] == stream.id
    data = broadcast_args[1]
    assert isinstance(data, bytes)
