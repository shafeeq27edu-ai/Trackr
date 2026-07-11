import os
import cv2
import json
import numpy as np
import supervision as sv
import time
from typing import Dict, List, Any
from tracker.detector import YoloDetector
from tracker.tracker import ByteTrackerWrapper
from tracker.analytics import AnalyticsEngine
from config.settings import Settings
from core.logging import logger
from core.exceptions import VideoProcessingError
from core.job_manager import JobManager, JobStatus

def load_zones(zones_file: str, resolution_wh: tuple) -> List[Dict[str, Any]]:
    """Loads zone configurations and returns them along with their sv.PolygonZone objects."""
    if not os.path.exists(zones_file):
        return []
        
    try:
        with open(zones_file, "r") as f:
            zones_data = json.load(f)
            
        loaded_zones = []
        for z in zones_data:
            if not z.get("enabled", True):
                continue
                
            pts = np.array(z["coordinates"], dtype=np.int32)
            zone_obj = sv.PolygonZone(polygon=pts)
            
            loaded_zones.append({
                "id": z["id"],
                "name": z["name"],
                "zone_obj": zone_obj,
                "annotator": sv.PolygonZoneAnnotator(
                    zone=zone_obj, 
                    color=sv.Color.ROBOFLOW,
                    thickness=2,
                    text_thickness=1,
                    text_scale=0.5
                )
            })
        return loaded_zones
    except Exception as e:
        logger.warning(f"Failed to load zones from {zones_file}: {e}")
        return []

def process_video_file(
    input_path: str, 
    output_path: str, 
    detector: YoloDetector, 
    settings: Settings,
    job_id: str,
    job_manager: JobManager
) -> Dict[str, Any]:
    """
    Processes a video file through the object tracking and analytics pipeline.
    """
    logger.info(f"Starting processing for video: {input_path}")
    start_time = time.time()
    
    if not os.path.exists(input_path):
        error_msg = f"Source video not found at {input_path}"
        logger.error(error_msg)
        job_manager.update_job(job_id, status=JobStatus.FAILED, error=error_msg)
        raise FileNotFoundError(error_msg)
        
    job_dir = os.path.dirname(output_path)
    os.makedirs(job_dir, exist_ok=True)
    
    heatmap_path = os.path.join(job_dir, f"heatmap_{job_id}.png")
    
    # Initialize components
    video_info = sv.VideoInfo.from_video_path(input_path)
    tracker = ByteTrackerWrapper()
    analytics = AnalyticsEngine(log_dir=job_dir, fps=video_info.fps)
    
    # Load Zones
    zones_file = os.path.join("config", "zones.json")
    zones = load_zones(zones_file, video_info.resolution_wh)
    
    # Initialize annotators
    box_annotator = sv.BoundingBoxAnnotator()
    label_annotator = sv.LabelAnnotator()
    
    # Trace with configurable fading/length
    trace_annotator = sv.TraceAnnotator(
        thickness=2,
        trace_length=video_info.fps * 2, # 2 seconds tail
    )
    
    # Heatmap Annotator
    # Use standard settings. For supervision 0.20.0+, HeatMapAnnotator exists.
    try:
        heatmap_annotator = sv.HeatMapAnnotator()
        use_heatmap = True
    except AttributeError:
        # Fallback if supervision version doesn't support it
        logger.warning("sv.HeatMapAnnotator not found in this supervision version.")
        use_heatmap = False

    try:
        total_frames = video_info.total_frames
        job_manager.update_job(job_id, status=JobStatus.PROCESSING, stage="Processing frames")
        
        # We need an empty canvas for the heatmap to accumulate over the entire video
        if use_heatmap:
            heatmap_canvas = np.zeros((video_info.height, video_info.width, 3), dtype=np.uint8)
        
        # Process the video frame by frame
        # Attempt H.264 (avc1) first for better browser compatibility, fallback to mp4v if needed
        codec = "avc1"
        try:
            # Quick check if avc1 is supported
            test_writer = cv2.VideoWriter(
                output_path,
                cv2.VideoWriter_fourcc(*"avc1"),
                video_info.fps,
                video_info.resolution_wh,
            )
            if not test_writer.isOpened():
                codec = "mp4v"
            test_writer.release()
            if os.path.exists(output_path):
                os.remove(output_path)
        except Exception:
            codec = "mp4v"

        with sv.VideoSink(target_path=output_path, video_info=video_info, codec=codec) as sink:
            frame_idx = 0
            for frame in sv.get_video_frames_generator(input_path):
                # 1. Detect objects
                detections = detector.detect(frame, conf_threshold=settings.confidence_threshold)
                
                # 2. Track objects
                detections = tracker.update(detections)
                
                # 3. Process Analytics & Zone Triggers
                analytics.process_detections(detections, detector.model.names, frame_idx)
                
                has_tracks = detections.tracker_id is not None and len(detections.tracker_id) > 0
                
                # Zone processing
                if has_tracks:
                    for z in zones:
                        is_in_zone = z["zone_obj"].trigger(detections=detections)
                        analytics.process_zone_triggers(z["id"], is_in_zone, detections.tracker_id)
                
                # 4. Annotate (optimize: direct modification is safe as generator frames are not reused)
                annotated_frame = frame
                
                if use_heatmap and has_tracks:
                    heatmap_canvas = heatmap_annotator.annotate(scene=heatmap_canvas, detections=detections)
                
                if has_tracks:
                    labels = []
                    for class_id, confidence, tracker_id in zip(detections.class_id, detections.confidence, detections.tracker_id):
                        speed = analytics.get_track_speed(tracker_id)
                        direction = analytics.get_track_direction(tracker_id)
                        
                        label_parts = [f"#{tracker_id} {detector.model.names[class_id]}"]
                        if speed > 0:
                            label_parts.append(f"{speed:.1f} km/h")
                        if direction != "Unknown":
                            label_parts.append(direction)
                        labels.append(" | ".join(label_parts))
                    
                    annotated_frame = trace_annotator.annotate(scene=annotated_frame, detections=detections)
                    annotated_frame = box_annotator.annotate(scene=annotated_frame, detections=detections)
                    annotated_frame = label_annotator.annotate(
                        scene=annotated_frame, detections=detections, labels=labels
                    )
                    
                # Annotate zones
                for z in zones:
                    annotated_frame = z["annotator"].annotate(scene=annotated_frame)
                
                # 5. Add Analytics Overlay
                summary_text = analytics.get_summary_text()
                cv2.putText(
                    annotated_frame, 
                    f"Unique Counts: {summary_text}", 
                    (20, 40), 
                    cv2.FONT_HERSHEY_SIMPLEX, 
                    0.8, 
                    (0, 255, 255), 
                    2
                )
                
                # 6. Save to output video
                sink.write_frame(frame=annotated_frame)
                
                # Cleanup frame memory (let Python handle it automatically)
                frame_idx += 1
                
                # Update Job Progress (throttle updates)
                if frame_idx % 10 == 0 or frame_idx == total_frames:
                    progress_percentage = (frame_idx / total_frames) * 100 if total_frames > 0 else 0
                    current_fps = frame_idx / (time.time() - start_time)
                    job_manager.update_job(job_id, progress=progress_percentage, average_fps=current_fps)
                    
        duration = time.time() - start_time
        final_fps = frame_idx / duration if duration > 0 else 0
        logger.info(f"Successfully processed {frame_idx} frames in {duration:.2f} seconds (FPS: {final_fps:.2f}).")
        
        # Save Heatmap image
        if use_heatmap:
            cv2.imwrite(heatmap_path, heatmap_canvas)
            del heatmap_canvas
        
        # Generate final Session Summary
        summary = analytics.generate_session_summary(total_frames, duration)
        
        # Mark job as completed
        # Save output using the storage abstraction
        from core.storage.manager import storage_manager
        storage = storage_manager.get_provider()
        
        # In a real distributed scenario, we'd upload this file, then delete local.
        # Since it's local storage for now, this just ensures it exists.
        storage_ref = output_path
        if storage:
            # We could do storage.save(output_path, open(output_path, 'rb'))
            pass # Skipping actual move for this milestone to avoid breaking API, assuming local.
            
        job_manager.update_job(
            job_id, 
            status=JobStatus.COMPLETED, 
            output_path=output_path,
            analytics=summary,
            stage="Completed",
            average_fps=final_fps,
            processing_throughput=final_fps
        )
        
        # Explicitly store heatmap path in the job state dict to ensure API can find it
        # (Since Job model doesn't strictly have a heatmap_path, we'll store it by convention in output_path dir)
        
        return summary
    
    except Exception as e:
        logger.error(f"Error during video processing: {str(e)}", exc_info=True)
        job_manager.update_job(job_id, status=JobStatus.FAILED, error=str(e), stage="Failed")
        raise VideoProcessingError(f"Failed to process video: {str(e)}")
