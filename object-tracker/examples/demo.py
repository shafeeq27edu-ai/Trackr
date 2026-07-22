import os

import cv2
import supervision as sv

from tracker.analytics import AnalyticsEngine
from tracker.detector import YoloDetector
from tracker.tracker import ByteTrackerWrapper


def main():
    """
    Entry point for Step 1: Bare Detection.
    Reads a sample video, runs YOLOv8 detection, draws bounding boxes, and saves the output.
    """
    source_video_path = "data/sample_videos/sample.mp4"
    output_dir = "outputs/videos"
    output_video_path = os.path.join(output_dir, "output_analytics.mp4")

    os.makedirs(output_dir, exist_ok=True)

    if not os.path.exists(source_video_path):
        print(f"Error: Source video not found at {source_video_path}")
        return

    # Initialize the detector, tracker, and analytics engine
    detector = YoloDetector("yolov8n.pt")
    tracker = ByteTrackerWrapper()
    analytics = AnalyticsEngine()

    # Initialize annotators
    box_annotator = sv.BoundingBoxAnnotator()
    label_annotator = sv.LabelAnnotator()
    trace_annotator = sv.TraceAnnotator()

    # Get video info for saving
    video_info = sv.VideoInfo.from_video_path(source_video_path)

    print(f"Processing video: {source_video_path}")
    print(f"Resolution: {video_info.resolution_wh}, FPS: {video_info.fps}")

    # Process the video frame by frame
    with sv.VideoSink(target_path=output_video_path, video_info=video_info) as sink:
        frame_idx = 0
        for frame in sv.get_video_frames_generator(source_video_path):
            # 1. Detect objects
            detections = detector.detect(frame, conf_threshold=0.3)

            # 2. Track objects
            detections = tracker.update(detections)

            # 3. Process Analytics
            analytics.process_detections(detections, detector.model.names, frame_idx)

            # 4. Format labels
            labels = [
                f"#{tracker_id} {detector.model.names[class_id]} {confidence:.2f}"
                for class_id, confidence, tracker_id in zip(
                    detections.class_id, detections.confidence, detections.tracker_id
                )
            ]

            # 5. Annotate frame
            annotated_frame = trace_annotator.annotate(scene=frame.copy(), detections=detections)
            annotated_frame = box_annotator.annotate(scene=annotated_frame, detections=detections)
            annotated_frame = label_annotator.annotate(
                scene=annotated_frame, detections=detections, labels=labels
            )

            # 6. Add Analytics Overlay
            summary_text = analytics.get_summary_text()
            cv2.putText(
                annotated_frame,
                f"Unique Counts: {summary_text}",
                (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 255, 255),
                2,
            )

            # 7. Save to output video
            sink.write_frame(frame=annotated_frame)
            frame_idx += 1

    print(f"Processing complete. Output saved to {output_video_path}")


if __name__ == "__main__":
    main()
