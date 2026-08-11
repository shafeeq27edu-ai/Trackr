# Low-Level Design (LLD)

## Database Schema
The database uses SQLAlchemy with the following core entities (derived from `db/models.py`):

- **`users` Table:**
  - `id` (String, PK)
  - `email` (String, Unique)
  - `hashed_password` (String)
  - `name` (String, Nullable)
  - `role` (String, default: "Standard User")
  - `status` (String, default: "active")
  - `created_at` (DateTime)
  - `last_login` (DateTime, Nullable)
  - *Relationships:* `projects`, `jobs`, `audit_logs`, `streams`

- **`projects` Table:**
  - `id` (String, PK)
  - `name` (String)
  - `description` (String, Nullable)
  - `user_id` (String, FK -> `users.id`)
  - `created_at` (DateTime)
  - *Relationships:* `owner`, `jobs`

- **`jobs` Table:**
  - `id` (String, PK)
  - `filename` (String)
  - `status` (String, default: "QUEUED")
  - `progress` (Float, default: 0.0)
  - `stage` (String, default: "Job created")
  - `user_id` (String, FK -> `users.id`, Nullable)
  - `project_id` (String, FK -> `projects.id`, Nullable)
  - `start_time`, `completion_time` (DateTime)
  - `duration`, `average_fps`, `processing_throughput` (Float, Nullable)
  - `error`, `output_path`, `analytics` (String, Nullable)
  - *Relationships:* `owner`, `project`

- **`streams` Table:**
  - `id` (String, PK)
  - `source` (String)
  - `user_id` (String, FK -> `users.id`)
  - `created_at` (DateTime)
  - *Relationships:* `owner`

- **`audit_logs` Table:**
  - `id` (Integer, PK)
  - `user_id` (String, FK -> `users.id`, Nullable)
  - `action` (String)
  - `resource` (String, Nullable)
  - `timestamp` (DateTime)

## API Endpoint Reference
> **Note:** All endpoints under `/api/v1` except `auth/login`, `auth/register`, `auth/google/*`, and `health` require a valid JWT via the `Authorization: Bearer <token>` header.

### Auth (`/api/v1/auth`)
- `POST /register`: Accepts `UserCreate` (email, password, name), returns `UserResponse`.
- `POST /login`: Accepts `OAuth2PasswordRequestForm`, returns a JWT `Token`.
- `GET /me`: Returns the currently authenticated `UserResponse`.
- `GET /google/login`: Initiates OAuth flow, redirects to Google.
- `GET /google/callback`: Receives Google callback, provisions/logs in user, redirects frontend with `auth_code`.
- `POST /exchange`: Exchanges `auth_code` for a JWT `Token`.

### Jobs (`/api/v1/jobs`)
- `POST /`: Uploads a video file, creates a Job, and submits it to the execution backend.
- `GET /`: Lists jobs owned by the current user.
- `GET /{job_id}`: Retrieves details of a specific job (enforces IDOR).
- `DELETE /{job_id}`: Deletes a job and its output files.

### Streams (`/api/v1/streams`)
- `POST /`: Creates a new stream entity.
- `GET /`: Lists active streams for the user.
- `GET /{stream_id}`: Gets stream metadata.
- `POST /{stream_id}/start`: Spawns an asyncio task to process the live stream.
- `POST /{stream_id}/stop`: Sets the stream's stop event.
- `POST /{stream_id}/record` & `stop_record`: Toggles stream recording to the disk.
- `WS /live/{stream_id}`: WebSocket connection for receiving annotated frames. Requires JWT passed as `?token=`.
- `WS /status`: WebSocket connection to broadcast stream status changes to the client.

### System (`/api/v1/system`)
- `GET /info`: Retrieves system environment and capabilities (requires auth).
- `GET /health`: Returns basic health check (does NOT require auth).

## Core Module Breakdown
- **`tracker/detector.py` (`YoloDetectorPlugin`):** Wraps Ultralytics YOLOv8 inference. Its `load_model` method attempts ONNX export for CPU acceleration. Provides `detect()` and `detect_batch()` methods returning `sv.Detections`.
- **`tracker/tracker.py` (`ByteTrackerPlugin`):** Wraps `sv.ByteTrack`. Its `update()` method takes raw detections and assigns persistent track IDs across frames.
- **`core.job_manager.JobManager`**: Provides abstraction over database operations for jobs (e.g., `create_job`, `update_job`, `get_job`).
- **`core.stream_manager.StreamManager`**: Maintains in-memory state of live streams (status, active WebSockets, asyncio tasks) and handles broadcasting frames to connected WebSocket clients.

## Key Sequence Walkthroughs
- **Video Upload Reaching COMPLETED:**
  1. Client calls `POST /jobs` with an `.mp4` file.
  2. `JobService.upload_video` saves the file to `outputs/temp/`.
  3. `JobManager` writes the initial job state to the DB (`INITIALIZING`).
  4. `JobService` calls `ExecutionBackend.submit_job()`, sending it to Celery.
  5. Celery Worker executes `_process_video_wrapper`, initializing YOLO and processing the video frame-by-frame.
  6. The worker writes the output file and uses `JobManager` to update the DB status to `COMPLETED` along with metrics (`average_fps`, etc.).
- **Google OAuth Login:**
  1. User clicks login, hitting `/auth/google/login`.
  2. Redirected to Google; authenticates and returns to `/auth/google/callback`.
  3. Backend verifies the token, looks up/creates the User, and records a `LOGIN_SUCCESS_GOOGLE` audit log.
  4. Backend generates a UUID `auth_code`, stores the JWT in memory, and redirects to frontend `/?auth_code=...`.
  5. Frontend mounts, sees the code, and calls `POST /auth/exchange`.
  6. Backend invalidates the code and returns the JWT.
- **IDOR Protection on Stream Access:**
  1. Client makes a request to `DELETE /streams/{stream_id}`.
  2. `get_current_user` dependency resolves the caller to `User A`.
  3. Endpoint fetches the stream from `StreamManager`.
  4. Explicit check: `if stream.user_id != current_user.id: raise HTTPException(404)`.
  5. User B receives a 404 Not Found, protecting User A's stream.

## Security Implementation Notes
- **Password Hashing:** Implemented using `passlib` with `bcrypt` algorithms.
- **JWT Authentication:** Tokens signed using `HS256` and the application's `SECRET_KEY`, possessing an expiration limit.
- **CORS:** Controlled via FastAPI middleware, currently allowing configured `BACKEND_CORS_ORIGINS`.
- **OAuth Code-Exchange:** Mitigates the risk of leaking tokens in HTTP referer headers or browser history.
- **Data Isolation (IDOR Mitigation):** Every resource (Projects, Jobs, Streams) natively ties to a `user_id`. Endpoint dependencies systematically query filtering on `current_user.id`, ensuring hard isolation between tenants (Phase 1 security fixes applied).
