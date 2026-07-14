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
from core.profiler import system_profiler

import threading

class StreamReader:
    """Background thread to continuously grab the latest frame, skipping backlog."""
    def __init__(self, source_id):
        self.source_id = source_id
        self.cap = None
        self.ret = False
        self.frame = None
        self.running = True
        self.lock = threading.Lock()
        self.is_opened = False
        self.fps = 30
        self.frame_id = 0
        
    def start(self):
        logger.info(f"StreamReader: Attempting to open video source {self.source_id}")
        self.cap = cv2.VideoCapture(self.source_id)
        if self.cap.isOpened():
            logger.info(f"StreamReader: Successfully opened video source {self.source_id}")
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            self.is_opened = True
            fps_prop = self.cap.get(cv2.CAP_PROP_FPS)
            if fps_prop > 0:
                self.fps = fps_prop
            self.ret, self.frame = self.cap.read()
            if not self.ret:
                logger.warning(f"StreamReader: Opened source {self.source_id} but failed to read initial frame.")
            self.thread = threading.Thread(target=self._update, daemon=True)
            self.thread.start()
        else:
            logger.error(f"StreamReader: Failed to open video source {self.source_id}")
            
    def _update(self):
        while self.running and self.cap.isOpened():
            with system_profiler.measure("camera_read"):
                ret, frame = self.cap.read()
            with self.lock:
                self.ret = ret
                if ret:
                    self.frame = frame
                    self.frame_id += 1
                    
    def read(self):
        with self.lock:
            return self.ret, (self.frame.copy() if self.frame is not None else None), self.frame_id
            
    def release(self):
        self.running = False
        if hasattr(self, 'thread'):
            self.thread.join(timeout=1.0)
        if self.cap:
            self.cap.release()

class InferenceWorker:
    """Background thread to run heavy YOLO inference decoupled from the video stream."""
    def __init__(self, detector, tracker, reader):
        self.detector = detector
        self.tracker = tracker
        self.reader = reader
        self.latest_detections = None
        self.detections_id = 0
        self.running = True
        self.lock = threading.Lock()
        
    def start(self):
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        
    def _run(self):
        last_frame_id = -1
        while self.running:
            ret, frame, frame_id = self.reader.read()
            if not ret or frame is None or frame_id == last_frame_id:
                time.sleep(0.01)
                continue
                
            last_frame_id = frame_id
                
            # Heavy inference on downscaled grid for speed
            t0 = time.time()
            with system_profiler.measure("yolo_inference"):
                detections = self.detector.detect(frame, 0.25, imgsz=640)
            t1 = time.time()
            with system_profiler.measure("tracking"):
                detections = self.tracker.update(detections)
            t2 = time.time()
            
            # Throttle logging to prevent spam, log every 100th inference
            if self.detections_id % 100 == 0:
                logger.debug(f"InferenceWorker: detect={t1-t0:.3f}s, track={t2-t1:.3f}s")
            
            with self.lock:
                self.latest_detections = detections
                self.detections_id += 1
                
    def get_latest(self):
        with self.lock:
            return self.latest_detections, self.detections_id
            
    def stop(self):
        self.running = False
        if hasattr(self, 'thread'):
            self.thread.join(timeout=1.0)

async def process_live_stream(stream_id: str, source: str, stream_manager: StreamManager, detector: YoloDetector):
    """
    Continuous background loop for processing a live video stream.
    Uses StreamReader for zero-latency frame skipping and InferenceWorker to decouple AI.
    """
    logger.info(f"Starting live stream: {stream_id} from source: {source}")
    stream_manager.update_stream(stream_id, status=StreamStatus.PLAYING)
    
    # Try converting source to int (for webcam 0, 1)
    try:
        source_id = int(source)
    except ValueError:
        source_id = source
        
    reader = StreamReader(source_id)
    await asyncio.to_thread(reader.start)
    
    if not reader.is_opened:
        logger.error(f"Failed to open stream source: {source}")
        stream_manager.update_stream(stream_id, status=StreamStatus.FAILED, error="Unable to open webcam. Camera may be in use.", camera_connected=False)
        return

    tracker = ByteTrackerWrapper()
    inference_worker = InferenceWorker(detector, tracker, reader)
    inference_worker.start()
    # Assume 30fps for analytics initially, can adjust dynamically if needed
    fps = reader.fps
    
    analytics = AnalyticsEngine(log_dir="outputs/live", fps=fps)
    
    box_annotator = sv.BoundingBoxAnnotator()
    label_annotator = sv.LabelAnnotator()
    trace_annotator = sv.TraceAnnotator(trace_length=int(fps))
    
    stream = stream_manager.get_stream(stream_id)
    
    last_process_time = time.time()
    frames_processed = 0
    start_time = time.time()
    last_frame_id = -1
    last_detections_id_local = -1

    try:
        while True:
            # Check for stop signal
            if stream and stream.stop_event and stream.stop_event.is_set():
                logger.info(f"Stream {stream_id} received stop signal.")
                break
                
            # Read the latest frame from the background thread
            ret, frame, frame_id = reader.read()
            
            if frame_id == last_frame_id:
                # No new frame from the camera yet, sleep briefly to prevent 1000 FPS CPU spikes
                await asyncio.sleep(0.01)
                continue
                
            last_frame_id = frame_id
            
            if not ret or frame is None:
                logger.warning(f"Stream {stream_id} ended or failed to read frame. Attempting reconnect in 2s...")
                stream_manager.update_stream(stream_id, error="Camera feed lost. Reconnecting...", camera_connected=False)
                await asyncio.sleep(2)
                reader.release()
                reader = StreamReader(source_id)
                await asyncio.to_thread(reader.start)
                if not reader.is_opened:
                    stream_manager.update_stream(stream_id, status=StreamStatus.FAILED, error="Unable to reconnect to camera.")
                    break
                stream_manager.update_stream(stream_id, status=StreamStatus.PLAYING, error=None, camera_connected=True)
                continue
                
            # Frame skipping (simple approach): 
            # Detections are generated completely asynchronously by InferenceWorker.
            # We simply fetch the latest available boxes to overlay on this frame, guaranteeing zero latency.
            
            detections, detections_id = inference_worker.get_latest()
            
            annotated_frame = frame
            if detections is not None:
                # 3. Analytics (Only process if this is a new set of detections to avoid double counting)
                if last_detections_id_local != detections_id:
                    analytics.process_detections(detections, detector.names, frames_processed)
                    last_detections_id_local = detections_id
                
                # 4. Annotate (optimize: in-place modification of frame is safe for webcam loops)
                if detections.tracker_id is not None and len(detections.tracker_id) > 0:
                    with system_profiler.measure("annotation"):
                        labels = []
                        for class_id, confidence, tracker_id in zip(detections.class_id, detections.confidence, detections.tracker_id):
                            speed = analytics.get_track_speed(tracker_id)
                            direction = analytics.get_track_direction(tracker_id)
                            try:
                                class_name = detector.names[int(class_id)] if getattr(detector, 'names', None) else f"class_{class_id}"
                            except (IndexError, KeyError, TypeError):
                                class_name = f"class_{class_id}"
                            label_parts = [f"#{tracker_id} {class_name}"]
                            if speed > 0:
                                label_parts.append(f"{speed:.1f} km/h")
                            if direction != "Unknown":
                                label_parts.append(direction)
                            labels.append(" | ".join(label_parts))
                            
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
                stream_manager.update_stream(
                    stream_id, 
                    fps=round(current_fps, 2),
                    frames_processed=frames_processed,
                    camera_connected=True,
                    total_detections=analytics.total_detections if hasattr(analytics, 'total_detections') else 0
                )
                
            # Encode frame to JPEG
            with system_profiler.measure("video_encode"):
                _, buffer = cv2.imencode('.jpg', annotated_frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            
            # Push raw binary blob to WebSocket
            try:
                with system_profiler.measure("websocket_send"):
                    await stream_manager.broadcast_bytes_to_stream(stream_id, buffer.tobytes())
            except Exception as e:
                logger.error(f"Stream {stream_id} WebSocket broadcast failed: {e}")
            
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
            
            # Yield to event loop to allow websockets to transmit
            await asyncio.sleep(0.001)

    except Exception as e:
        logger.error(f"Error in stream {stream_id}: {str(e)}", exc_info=True)
        stream_manager.update_stream(stream_id, status=StreamStatus.FAILED, error=str(e))
    finally:
        if 'inference_worker' in locals():
            inference_worker.stop()
        reader.release()
        if stream and hasattr(stream, "writer") and stream.writer:
            stream.writer.release()
            stream.writer = None
        stream = stream_manager.get_stream(stream_id)
        if stream and stream.status != StreamStatus.FAILED:
            stream_manager.update_stream(stream_id, status=StreamStatus.STOPPED)
        logger.info(f"Stream {stream_id} stopped.")
