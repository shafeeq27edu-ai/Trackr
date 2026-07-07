# AGENTS.md — object-tracker (YOLOv8 + ByteTrack)

Read this fully before doing anything. This file is the source of truth for
scope, order of work, and non-negotiables. Skills in `.agents/skills/` add
detail on demand — don't duplicate their content here, just point to them.

## Project one-liner
General object tracking system: YOLOv8 detection → ByteTrack tracking →
annotation → analytics (unique counts, dwell time, zone entry/exit) →
Streamlit UI, optionally served via FastAPI, deployed to HF Spaces/Render.

## Tech stack (do not substitute without asking)
- Detection: YOLOv8 (Ultralytics)
- Tracking: ByteTrack via `supervision` (Roboflow) — do not hand-roll tracker glue code
- Video/image I/O: OpenCV
- UI: Streamlit
- API (optional): FastAPI
- Logging: SQLite or CSV
- Python 3.10+, venv or conda

## Fixed project structure
```
object-tracker/
├── app.py
├── tracker/
│   ├── detector.py
│   ├── tracker.py
│   ├── annotator.py
│   └── analytics.py
├── data/sample_videos/
├── outputs/videos/, outputs/logs.csv
├── requirements.txt
├── README.md
└── demo.gif
```
New files go in these locations. Don't invent a different layout mid-project.

## Build order — hard sequence, do not skip or merge steps
1. **Bare detection** — YOLOv8 on a sample video, draw boxes, no tracking.
2. **Tracking** — add ByteTrack via `supervision`; verify IDs stay stable
   through brief occlusion/overlap.
3. **Analytics** — unique count per class (dedup by track ID, not per-frame),
   optional zone entry/exit, CSV logging (timestamp, track_id, class, position).
4. **Streamlit UI** — upload → annotated video output → stats table/chart.
5. **Polish + deploy** — README, deploy to HF Spaces or Render, demo GIF.

Each step must run and be verified before starting the next. If asked to
"just build the whole thing," still work through these steps in order and
checkpoint after each one — see the `planning-protocol` skill.

## Non-negotiables
- Never invent a tracker from scratch — use `supervision`'s ByteTrack integration.
- Object counts must be deduplicated by track ID, never raw per-frame detections.
- Every new capability starts with a plan artifact, not code (see `planning-protocol` skill).
- Keep context/token usage lean — see `token-efficient-execution` skill before
  reading/writing large files or repeating prior output.
- Domain specifics (YOLO output format, IoU/confidence matching, occlusion
  edge cases) live in the `cv-tracking-standards` skill — consult it instead
  of guessing.

## When stuck or ambiguous
State the assumption you're making, proceed with the most reasonable default
per the build order above, and flag it in the plan artifact rather than
pausing the whole pipeline.
