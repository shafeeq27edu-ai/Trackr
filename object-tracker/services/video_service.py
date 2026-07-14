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
                "polygon_pts": pts,
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
    
    import asyncio
    
    if not os.path.exists(input_path):
        error_msg = f"Source video not found at {input_path}"
        logger.error(error_msg)
        asyncio.run(job_manager.update_job(job_id, status=JobStatus.FAILED, error=error_msg))
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
        asyncio.run(job_manager.update_job(job_id, status=JobStatus.PROCESSING, stage="Processing frames"))
        
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

        # Dynamic stride for massive speedup
        stride = 2 if video_info.fps > 20 else 1
        
        # Modify video info to reduce FPS mathematically so we only encode ONCE!
        output_video_info = sv.VideoInfo(
            width=video_info.width,
            height=video_info.height,
            fps=video_info.fps / stride,
            total_frames=video_info.total_frames // stride
        )
        
        with sv.VideoSink(target_path=output_path, video_info=output_video_info, codec=codec) as sink:
            frame_idx = 0
            batch_size = 4
            frame_batch = []
            
            def process_batch():
                nonlocal frame_idx
                if not frame_batch:
                    return
                
                # 1. Detect objects in batch
                batch_detections = detector.detect_batch(frame_batch, conf_threshold=settings.confidence_threshold, imgsz=640)
                
                for b_frame, b_detections in zip(frame_batch, batch_detections):
                    # 2. Track objects
                    b_detections = tracker.update(b_detections)
                    
                    # 3. Process Analytics & Zone Triggers
                    analytics.process_detections(b_detections, detector.names, frame_idx)
                    
                    has_tracks = b_detections.tracker_id is not None and len(b_detections.tracker_id) > 0
                    
                    if has_tracks:
                        for z in zones:
                            is_in_zone = z["zone_obj"].trigger(detections=b_detections)
                            analytics.process_zone_triggers(z["id"], is_in_zone, b_detections.tracker_id)
                            
                    # 4. Annotate
                    annotated_frame = b_frame
                    
                    if use_heatmap and has_tracks:
                        nonlocal heatmap_canvas
                        heatmap_canvas = heatmap_annotator.annotate(scene=heatmap_canvas, detections=b_detections)
                        
                    if has_tracks:
                        labels = []
                        for class_id, confidence, tracker_id in zip(b_detections.class_id, b_detections.confidence, b_detections.tracker_id):
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
                            
                        annotated_frame = trace_annotator.annotate(scene=annotated_frame, detections=b_detections)
                        annotated_frame = box_annotator.annotate(scene=annotated_frame, detections=b_detections)
                        annotated_frame = label_annotator.annotate(
                            scene=annotated_frame, detections=b_detections, labels=labels
                        )
                        
                    for z in zones:
                        cv2.polylines(annotated_frame, [z["polygon_pts"]], isClosed=True, color=(0, 255, 0), thickness=2)
                        label_pos = tuple(z["polygon_pts"][0])
                        cv2.putText(annotated_frame, z["name"], label_pos, cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                        
                    summary_text = analytics.get_summary_text()
                    cv2.putText(annotated_frame, f"Unique Counts: {summary_text}", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
                    
                    # 6. Save to output video
                    sink.write_frame(frame=annotated_frame)
                    
                    frame_idx += stride
                    
                    # Update Job Progress (throttle updates)
                    if frame_idx % (10 * stride) == 0 or frame_idx >= total_frames:
                        progress_percentage = min((frame_idx / total_frames) * 100, 100.0) if total_frames > 0 else 0
                        current_fps = frame_idx / (time.time() - start_time)
                        asyncio.run(job_manager.update_job(job_id, progress=progress_percentage, average_fps=current_fps))
                
                frame_batch.clear()

            for frame in sv.get_video_frames_generator(input_path, stride=stride):
                frame_batch.append(frame)
                if len(frame_batch) >= batch_size:
                    process_batch()
            
            # Process any remaining frames
            process_batch()
                    
        duration = time.time() - start_time
        final_fps = frame_idx / duration if duration > 0 else 0
        logger.info(f"Successfully processed {frame_idx} frames in {duration:.2f} seconds (FPS: {final_fps:.2f}).")
        
        # Save Heatmap image
        if use_heatmap:
            cv2.imwrite(heatmap_path, heatmap_canvas)
            del heatmap_canvas
        
        # Generate final Session Summary
        summary = analytics.generate_session_summary(total_frames, duration)
        
        # Post-process with FFmpeg only if we fell back to mp4v (not browser-compatible)
        if codec != "avc1":
            import subprocess
            asyncio.run(job_manager.update_job(job_id, status=JobStatus.PROCESSING, stage="Finalizing Video (Encoding)"))
            temp_output = output_path + ".temp.mp4"
            os.rename(output_path, temp_output)
            try:
                subprocess.run([
                    "ffmpeg", "-y", "-i", temp_output,
                    "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                    "-pix_fmt", "yuv420p", output_path
                ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                os.remove(temp_output)
            except Exception as e:
                logger.error(f"FFmpeg conversion failed: {e}. Keeping original.")
                if os.path.exists(temp_output):
                    os.rename(temp_output, output_path)
        else:
            logger.info("avc1 codec succeeded, skipping FFmpeg re-encode.")
        
        # Clean up temp input file to prevent disk fill
        try:
            if os.path.exists(input_path):
                os.remove(input_path)
                logger.info(f"Cleaned up temp input file: {input_path}")
        except Exception as e:
            logger.warning(f"Failed to clean up temp file {input_path}: {e}")

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
            
        asyncio.run(job_manager.update_job(
            job_id, 
            status=JobStatus.COMPLETED, 
            output_path=output_path,
            analytics=summary,
            stage="Completed",
            average_fps=final_fps,
            processing_throughput=final_fps
        ))
        
        # Explicitly store heatmap path in the job state dict to ensure API can find it
        # (Since Job model doesn't strictly have a heatmap_path, we'll store it by convention in output_path dir)
        
        return summary
    
    except Exception as e:
        logger.error(f"Error during video processing: {str(e)}", exc_info=True)
        asyncio.run(job_manager.update_job(job_id, status=JobStatus.FAILED, error=str(e), stage="Failed"))
        raise VideoProcessingError(f"Failed to process video: {str(e)}")
