import cv2
import time
import asyncio
import numpy as np
import supervision as sv
import base64
from tracker.detector import YoloDetector
from tracker.tracker import ByteTrackerWrapper
from tracker.analytics import AnalyticsEngine
from core.stream_manager import StreamManager, StreamStatus
from core.logging import logger

async def process_live_stream(stream_id: str, source: str, stream_manager: StreamManager, detector: YoloDetector):
    """
    Continuous background loop for processing a live video stream.
    Drops frames if processing falls behind.
    """
    logger.info(f"Starting live stream: {stream_id} from source: {source}")
    stream_manager.update_stream(stream_id, status=StreamStatus.PLAYING)
    
    # Try converting source to int (for webcam 0, 1)
    try:
        source_id = int(source)
    except ValueError:
        source_id = source
        
    cap = cv2.VideoCapture(source_id)
    if not cap.isOpened():
        logger.error(f"Failed to open stream source: {source}")
        stream_manager.update_stream(stream_id, status=StreamStatus.FAILED, error="Failed to open source")
        return

    tracker = ByteTrackerWrapper()
    # Assume 30fps for analytics initially, can adjust dynamically if needed
    fps_prop = cap.get(cv2.CAP_PROP_FPS)
    fps = fps_prop if fps_prop > 0 else 30
    
    analytics = AnalyticsEngine(log_dir="outputs/live", fps=fps)
    
    box_annotator = sv.BoxAnnotator()
    label_annotator = sv.LabelAnnotator()
    trace_annotator = sv.TraceAnnotator(trace_length=int(fps))
    
    stream = stream_manager.get_stream(stream_id)
    
    last_process_time = time.time()
    frames_processed = 0
    start_time = time.time()

    try:
        while True:
            # Check for stop signal
            if stream and stream.stop_event and stream.stop_event.is_set():
                logger.info(f"Stream {stream_id} received stop signal.")
                break
                
            ret, frame = cap.read()
            if not ret:
                logger.warning(f"Stream {stream_id} ended or failed to read frame. Attempting reconnect in 2s...")
                await asyncio.sleep(2)
                cap = cv2.VideoCapture(source_id)
                continue
                
            # Frame skipping (simple approach): 
            # If we are processing slower than the camera produces frames, we can grab to clear buffer.
            # (cv2.VideoCapture implicitly buffers, calling grab() helps skip).
            # We will process this frame, then yield to asyncio to send.
            
            # 1. Detect
            detections = detector.detect(frame, conf_threshold=0.3)
            
            # 2. Track
            detections = tracker.update(detections)
            
            # 3. Analytics
            analytics.process_detections(detections, detector.model.names, frames_processed)
            
            # 4. Annotate
            annotated_frame = frame.copy()
            if detections.tracker_id is not None and len(detections.tracker_id) > 0:
                labels = [
                    f"#{tracker_id} {detector.model.names[class_id]} {confidence:.2f}"
                    for class_id, confidence, tracker_id in zip(detections.class_id, detections.confidence, detections.tracker_id)
                ]
                annotated_frame = trace_annotator.annotate(scene=annotated_frame, detections=detections)
                annotated_frame = box_annotator.annotate(scene=annotated_frame, detections=detections)
                annotated_frame = label_annotator.annotate(scene=annotated_frame, detections=detections, labels=labels)
                
            # Embed analytics text (Optional, if we want it in the stream)
            summary_text = analytics.get_summary_text()
            cv2.putText(annotated_frame, f"Unique: {summary_text}", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,255,255), 2)
            
            # Calculate FPS
            now = time.time()
            elapsed = now - last_process_time
            current_fps = 1.0 / elapsed if elapsed > 0 else 0
            last_process_time = now
            
            # Throttle stream updates
            if frames_processed % 15 == 0:
                stream_manager.update_stream(stream_id, fps=round(current_fps, 2))
                
            # Encode frame to JPEG
            _, buffer = cv2.imencode('.jpg', annotated_frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            b64_frame = base64.b64encode(buffer).decode('utf-8')
            
            # Push to WebSocket
            message = {
                "frame": b64_frame,
                "fps": round(current_fps, 2),
                "analytics": {
                    "summary_text": summary_text,
                    "traffic_stats": analytics.traffic_stats,
                }
            }
            
            await stream_manager.broadcast_to_stream(stream_id, message)
            
            # Recording logic
            if stream and stream.is_recording and stream.recording_path:
                if not hasattr(stream, "writer") or stream.writer is None:
                    h, w = annotated_frame.shape[:2]
                    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                    stream.writer = cv2.VideoWriter(stream.recording_path, fourcc, fps, (w, h))
                stream.writer.write(annotated_frame)
            elif stream and hasattr(stream, "writer") and stream.writer:
                stream.writer.release()
                stream.writer = None
            
            frames_processed += 1
            
            del frame
            del annotated_frame
            
            # Yield to event loop to allow websockets to transmit
            await asyncio.sleep(0.001)

    except Exception as e:
        logger.error(f"Error in stream {stream_id}: {str(e)}", exc_info=True)
        stream_manager.update_stream(stream_id, status=StreamStatus.FAILED, error=str(e))
    finally:
        cap.release()
        if stream and hasattr(stream, "writer") and stream.writer:
            stream.writer.release()
            stream.writer = None
        if stream_manager.get_stream(stream_id).status != StreamStatus.FAILED:
            stream_manager.update_stream(stream_id, status=StreamStatus.STOPPED)
        logger.info(f"Stream {stream_id} stopped.")
