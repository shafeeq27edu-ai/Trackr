import json
import os
import time

import psutil
import supervision as sv

from config.settings import settings
from tracker.detector import YoloDetector
from tracker.tracker import ByteTrackerWrapper


def print_memory_usage():
    process = psutil.Process(os.getpid())
    mem_info = process.memory_info()
    print(f"Memory Usage: {mem_info.rss / 1024 / 1024:.2f} MB")


def run_benchmark():
    video_path = "data/sample_videos/sample.mp4"
    if not os.path.exists(video_path):
        print(f"Error: Sample video not found at {video_path}")
        return

    print("--- Benchmark Started ---")
    print_memory_usage()

    # Benchmark Model Loading
    start_time = time.time()
    detector = YoloDetector(settings.yolo_model_path)
    model_load_time = time.time() - start_time
    print(f"Model Load Time: {model_load_time:.4f} seconds")
    print_memory_usage()

    tracker = ByteTrackerWrapper()
    video_info = sv.VideoInfo.from_video_path(video_path)

    total_inference_time = 0.0
    total_tracking_time = 0.0
    frames_processed = 0

    print(f"Processing video: {video_path} (Total frames: {video_info.total_frames})")

    overall_start = time.time()

    for frame in sv.get_video_frames_generator(video_path):
        if frames_processed >= 100:  # process max 100 frames to save time in tests
            break

        t0 = time.time()
        detections = detector.detect(frame, conf_threshold=settings.confidence_threshold)
        t1 = time.time()
        total_inference_time += t1 - t0

        detections = tracker.update(detections)
        t2 = time.time()
        total_tracking_time += t2 - t1

        frames_processed += 1

    overall_time = time.time() - overall_start

    avg_inference = total_inference_time / frames_processed if frames_processed else 0
    avg_tracking = total_tracking_time / frames_processed if frames_processed else 0
    fps = frames_processed / overall_time if overall_time else 0

    print(f"--- Benchmark Results ({frames_processed} frames) ---")
    print(f"Average Inference Time: {avg_inference*1000:.2f} ms")
    print(f"Average Tracking Time: {avg_tracking*1000:.2f} ms")
    print(f"Overall Processing FPS: {fps:.2f}")
    print_memory_usage()

    results = {
        "model_load_time_sec": model_load_time,
        "avg_inference_ms": avg_inference * 1000,
        "avg_tracking_ms": avg_tracking * 1000,
        "fps": fps,
        "frames_processed": frames_processed,
    }

    os.makedirs("outputs/benchmarks", exist_ok=True)
    with open("outputs/benchmarks/baseline.json", "w") as f:
        json.dump(results, f, indent=4)


if __name__ == "__main__":
    run_benchmark()
