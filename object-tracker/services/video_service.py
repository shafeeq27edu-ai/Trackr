import os
import cv2
import supervision as sv
from typing import Dict
from tracker.detector import YoloDetector
from tracker.tracker import ByteTrackerWrapper
from tracker.analytics import AnalyticsEngine

def process_video_file(input_path: str, output_path: str) -> Dict[str, int]:
    """
    Processes a video file through the object tracking and analytics pipeline.
    
    Args:
        input_path: Path to the source video.
        output_path: Path where the annotated video will be saved.
        
    Returns:
        A dictionary containing the unique counts of tracked objects.
    """
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Source video not found at {input_path}")
        
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # Initialize the detector, tracker, and analytics engine
    detector = YoloDetector("yolov8n.pt")
    tracker = ByteTrackerWrapper()
    analytics = AnalyticsEngine()
    
    # Initialize annotators
    box_annotator = sv.BoxAnnotator()
    label_annotator = sv.LabelAnnotator()
    trace_annotator = sv.TraceAnnotator()
    
    # Get video info for saving
    video_info = sv.VideoInfo.from_video_path(input_path)
    
    # Process the video frame by frame
    with sv.VideoSink(target_path=output_path, video_info=video_info) as sink:
        frame_idx = 0
        for frame in sv.get_video_frames_generator(input_path):
            # 1. Detect objects
            detections = detector.detect(frame, conf_threshold=0.3)
            
            # 2. Track objects
            detections = tracker.update(detections)
            
            # 3. Process Analytics
            analytics.process_detections(detections, detector.model.names, frame_idx)
            
            # 4. Annotate if we have valid tracked detections
            if len(detections) > 0 and detections.tracker_id is not None and len(detections.tracker_id) > 0:
                labels = [
                    f"#{tracker_id} {detector.model.names[class_id]} {confidence:.2f}"
                    for class_id, confidence, tracker_id in zip(detections.class_id, detections.confidence, detections.tracker_id)
                ]
                
                annotated_frame = trace_annotator.annotate(scene=frame.copy(), detections=detections)
                annotated_frame = box_annotator.annotate(scene=annotated_frame, detections=detections)
                annotated_frame = label_annotator.annotate(
                    scene=annotated_frame, detections=detections, labels=labels
                )
            else:
                annotated_frame = frame.copy()
            
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
            
            # 7. Save to output video
            sink.write_frame(frame=annotated_frame)
            frame_idx += 1
            
    # Return the aggregated analytics summary
    counts = {class_name: len(ids) for class_name, ids in analytics.unique_counts.items()}
    return counts
