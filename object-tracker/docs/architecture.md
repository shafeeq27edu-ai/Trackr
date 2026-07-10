# Trackr Platform Architecture

Trackr is a modern, modular computer vision platform designed for scalability, ease of use, and enterprise extensibility.

## System Components

1. **API Server (FastAPI)**: Serves REST endpoints for managing projects, jobs, and configurations. It also serves WebSocket connections for real-time video streaming with bounding box overlays.
2. **Execution Backend**: Manages background processing. Pluggable to support local threading (default), Celery, or Ray for distributed clusters.
3. **Model Registry**: Lazy-loads and manages computer vision models in memory, preventing redundant VRAM allocation.
4. **Plugin Manager**: Discovers and loads custom `BaseDetector`, `BaseTracker`, and `BaseAnalytics` plugins.
5. **Event Bus**: A pub/sub system to emit system lifecycle events, allowing loose coupling between core logic and enterprise integrations.
6. **Storage Abstraction**: An interface (`StorageProvider`) for reading/writing media files to Local Disk, S3, or GCS.

## API Client Libraries Architecture

To support a wide developer ecosystem, Trackr officially supports multiple client libraries (Python, JavaScript/TypeScript, Go, Java). 

Instead of manually maintaining these libraries, Trackr uses a **Schema-Driven Code Generation** approach:

1. **OpenAPI as the Source of Truth**: The FastAPI backend automatically generates a strict OpenAPI 3.1 specification (`/openapi.json`). All route models, parameters, and authentication methods are strictly typed using Pydantic.
2. **Automated Code Generation**: During our CI/CD release process, we utilize `openapi-generator-cli` (or similar tools like `TypeSpec`) to compile the OpenAPI spec into native client libraries.
3. **Repository Strategy**:
   - `trackr-sdk` (Python): Built natively and co-located in the main repository for tight integration with the CLI.
   - `trackr-js` (TypeScript/JS): Generated and published to npm automatically.
   - `trackr-go` (Go): Generated and published to a dedicated GitHub repository automatically.

This ensures that our API clients are always 100% synchronized with the latest backend features without massive engineering overhead.
