# Frequently Asked Questions (FAQ) — Trackr v1.0

### Q1: What models does Trackr support out of the box?
Trackr v1.0 officially supports **YOLOv8** (specifically `yolov8n.pt`, `yolov8s.pt`, and `yolov8m.pt` weights) for object detection. It uses **ByteTrack** (via Roboflow Supervision) for multi-object tracking.

### Q2: Can I plug in a custom model?
Yes. Trackr features a pluggable Model Registry. You can register custom models by creating a class implementing `BaseDetector` and registering it with the `plugin_manager` (see [Plugins](plugins.md)).

### Q3: Why do tracking IDs change when an object is briefly behind a tree?
Trackr uses ByteTrack, which is a motion and overlap (IoU) based tracking algorithm. It does not use deep re-identification (Re-ID) appearance models. If an object is fully occluded (hidden) for longer than `max_time_lost` frames, its track will be deleted. When it reappears, it will receive a new ID. This is a design trade-off to keep inference extremely fast and low-latency.

### Q4: How is data isolated between different users?
Trackr is multi-tenant. Each User belongs to their own namespace. Projects and Jobs are linked to specific `user_id` values in the database, and the API verifies ownership on every request.

### Q5: Can I run Trackr without a GPU?
Yes. Trackr runs on standard CPU hosts by default. However, video processing throughput will be lower (8-15 FPS) compared to GPU acceleration (60-200 FPS).
