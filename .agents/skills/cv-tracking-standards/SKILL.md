---
name: cv-tracking-standards
description: Domain reference for YOLOv8 detection output, ByteTrack matching logic, and object-tracking edge cases. Triggers on any work in detector.py, tracker.py, annotator.py, or analytics.py, or questions about detection/tracking behavior.
---

# CV Tracking Standards

## YOLOv8 output format
- Each detection: bounding box (xyxy or xywh depending on API call),
  confidence score, class ID (maps to COCO 80-class names via `model.names`).
- Filter detections by class BEFORE passing to the tracker if the user only
  wants specific classes (e.g. "only people and cars") — don't track
  everything and filter downstream, that wastes tracker compute and can
  cause ID churn from filtered-out objects.
- Confidence threshold and IoU (NMS) threshold are separate knobs — don't
  conflate them; expose both as config, not hardcoded.

## ByteTrack matching logic (what it's actually doing)
- Two-stage association: first match high-confidence detections to existing
  tracks by IoU overlap between frames; then a second pass tries to match
  remaining low-confidence detections to still-unmatched tracks, which is
  what lets it survive brief occlusion instead of dropping the track.
- No re-identification/appearance model — matching is purely
  motion/overlap-based, which is why it's lightweight but can swap IDs if
  two similar objects cross paths and fully occlude each other.
- Tracks that go unmatched for more than a configurable number of frames are
  dropped; a new detection after that gets a new ID (this is expected
  behavior, not a bug — surface it in analytics rather than trying to
  "fix" it with re-identification unless the user asks for that upgrade).

## Required edge case handling
- **Object leaves frame, new one enters**: expect a new track ID; don't
  assume continuity.
- **Heavy overlap of two objects**: possible ID swap; log it as a known
  limitation in analytics rather than silently trusting IDs across the
  overlap event.
- **Object re-enters after leaving**: treated as a new ID by default (no
  re-ID model) — call this out explicitly if the user's use case needs
  persistent identity across full exits.

## Analytics rules
- Unique counts per class = count of distinct track IDs, never per-frame
  detection counts.
- Dwell time = (last frame seen − first frame seen) / fps for a given
  track ID.
- Zone entry/exit = check if a track's bounding-box centroid crosses a
  user-defined polygon/region between consecutive frames.
- Every log row needs: timestamp, track_id, class, position (and frame
  number) — this is required, not optional, for later debugging of ID
  swaps or drops.

## Library note
Use `supervision`'s `ByteTrack` class and annotation utilities
(`BoxAnnotator`, `LabelAnnotator`, trace annotators) rather than writing
custom box-drawing or tracker-glue code.
