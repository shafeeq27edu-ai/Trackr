# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-07-09

### Added
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
