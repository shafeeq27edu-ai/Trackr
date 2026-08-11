# Product Requirements Document (PRD)

## Problem Statement
Trackr addresses the need for a scalable, end-to-end platform for both real-time and offline video object detection, tracking, and analytics. It bridges the gap between raw video footage and actionable insights by providing robust tracking pipelines integrated with an easy-to-use user interface and comprehensive backend management.

## Target Users / Use Cases
- **Security Monitoring:** Analyzing live RTSP camera feeds to detect intrusions or monitor secured areas.
- **Traffic Analysis:** Estimating vehicle speeds, counting vehicles, and analyzing traffic flow through heatmaps.
- **Retail & Foot-Traffic Analytics:** Tracking customer movement, identifying highly trafficked areas, and performing overall crowd counting.

## Core Features
- **Offline Batch Video Processing:** Users can upload video files (.mp4, .avi, .mov), which are queued and processed asynchronously by worker nodes.
- **Live Streaming:** Support for processing real-time video sources (RTSP streams or local files) and serving the output directly to the frontend via WebSockets.
- **Object Detection & Persistent Tracking:** Built-in detection using YOLOv8 (with ONNX Runtime acceleration and PyTorch fallback) and persistent object tracking across frames using ByteTrack.
- **Analytics Dashboard:** Metrics such as classification counts, speed estimation, and activity heatmaps.
- **Export Capabilities:** Users can export tracked videos, analytical CSV data, and generated heatmaps.
- **Authentication & Security:** Local email/password authentication (with bcrypt hashing) and Google OAuth login integration.
- **Organization & Multi-Tenancy:** Users can manage their tasks through isolated, per-user projects and jobs.

## Explicit Non-Goals / Current Limitations
- **Webcam Access in Docker on Windows:** The application cannot stream directly from a host webcam when the backend is run in Docker on Windows (WSL2 cannot easily access host cameras). In these environments, RTSP streams or local video files are the supported live input methods, or users must run the application natively via hybrid mode (`run_dev.ps1`).
- **Distributed Video Chunking:** Currently, offline video processing works on a single file per worker rather than splitting a single video into chunks for distributed map-reduce processing.

## Success Criteria
- **Functional:** 
  - Jobs transition from QUEUED to COMPLETED successfully with correctly rendered bounding boxes and analytics.
  - Live streams can be started, stopped, and recorded successfully through the frontend.
- **Non-Functional:**
  - Reasonable processing FPS achieved through ONNX Runtime acceleration on CPU or via PyTorch on GPU.
  - Authentication and authorization strictly enforced across all user scopes, preventing unauthorized data access.
