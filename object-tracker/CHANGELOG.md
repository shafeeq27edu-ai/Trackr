# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-07-10

### Productization & GA Hardening
- **Security**: Hardened JWT signing by removing hardcoded secrets and supporting environment-based `SECRET_KEY` overrides.
- **Analytics Compatibility**: Added `process_detections` wrapper to `AnalyticsEnginePlugin` to restore backward-compatibility for existing integrations and unit tests.
- **Dependency Hardening**: Pinned all runtime and development packages to exact compatible versions and removed duplicates from `requirements.txt`.
- **System Documentation**: Replaced all MkDocs documentation placeholders with detailed guides for Installation, Quickstart, APIs, Monitoring, Security, Backups, Maintenance, and Runbooks.
- **Test Integrity**: Patched unit tests for the detector and job APIs to match the lazy-loading model manager lifecycle and authentication requirements.

### Core Architecture Features
- **Core Processing Pipeline**: YOLOv8 detection and ByteTrack multi-object tracking.
- **Advanced Analytics**: Zone intrusion detection, dwell time analysis, heatmap generation.
- **Background Jobs**: Asynchronous video processing with `JobManager`.
- **Live Streaming**: Real-time RTSP/Webcam processing and WebSocket streaming.
- **Authentication & Projects**: JWT-based authentication, user registration, and isolated project workspaces (SQLite + SQLAlchemy).
- **Observability**: `/metrics` (Prometheus), `/health`, `/ready`, and `/live` endpoints.
- **Structured Logging**: JSON logging support for production via `python-json-logger`.
- **Containerization**: Full Docker support with `backend.Dockerfile`, `frontend.Dockerfile`, and `docker-compose.yml`.
- **CI/CD**: GitHub Actions workflow for linting, testing, and Docker build validation.
- **Enterprise Architecture**: Extensible Plugin Manager and Model Registry.
- **SDK & CLI**: Official Python SDK (`trackr-sdk`) and Typer-based CLI.
- **Event System**: In-memory pub/sub `EventBus` for decoupled component communication.
- **Storage Abstraction**: `StorageProvider` interface for Local/Cloud output storage.
- **Developer Documentation**: MkDocs-based documentation site and example projects.
- **Dashboard**: Streamlit frontend for interacting with the platform.
