# REST API & WebSockets Reference — Trackr v1.0

The FastAPI backend exposes endpoints for authentication, project namespaces, batch video processing jobs, and real-time live streaming.

---

## 1. Authentication (`/api/v1/auth`)

### 1.1 Register User
* **Method & Path**: `POST /api/v1/auth/register`
* **Request Body**:
  ```json
  {
    "email": "user@example.com",
    "password": "strongpassword123",
    "name": "Alex Smith"
  }
  ```
* **Response**: `200 OK` returning the user model (excluding password hashes).

### 1.2 Login User
* **Method & Path**: `POST /api/v1/auth/login`
* **Request Header**: `Content-Type: application/x-www-form-urlencoded`
* **Request Body**: `username=user@example.com&password=strongpassword123`
* **Response**:
  ```json
  {
    "access_token": "eyJhbGciOi...",
    "token_type": "bearer"
  }
  ```

---

## 2. Workspaces & Projects (`/api/v1/projects`)

All endpoints in this group require the `Authorization: Bearer <token>` header.

* **`GET /api/v1/projects`**: Lists all projects owned by the authenticated user.
* **`POST /api/v1/projects`**: Creates a new project workspace.
  ```json
  {
    "name": "Intersection Traffic Cam"
  }
  ```

---

## 3. Video Processing Jobs (`/api/v1/jobs`)

All endpoints in this group require the `Authorization: Bearer <token>` header.

### 3.1 Upload Video for Processing
* **Method & Path**: `POST /api/v1/jobs/upload`
* **Request Body (Multipart Form-Data)**:
  - `file`: Bounding MP4 video file.
  - `project_id`: Optional project UUID.
* **Response**:
  ```json
  {
    "job_id": "a7cf837b-4f91-4860-ae7d-2afa1cc0ce32",
    "status": "INITIALIZING",
    "message": "Job successfully queued for processing."
  }
  ```

### 3.2 Get Job Status
* **Method & Path**: `GET /api/v1/jobs/{job_id}`
* **Response**: Returns progress percentage, current stage, and status (`QUEUED`, `PROCESSING`, `COMPLETED`, `FAILED`).

### 3.3 Fetch Job Results
* **`GET /api/v1/jobs/{job_id}/analytics`**: Returns aggregated session counts, dwell times, and zone exit/entries in JSON.
* **`GET /api/v1/jobs/{job_id}/heatmap`**: Returns the accumulated spatial heatmap image (`PNG` format).
* **`GET /api/v1/jobs/{job_id}/report`**: Returns raw frame-by-frame tracker coordinate telemetry in CSV format.

---

## 4. Live Streams (`/api/v1/streams`)

* **`POST /api/v1/streams`**: Registers a new stream source (e.g. RTSP URL or camera index).
* **`POST /api/v1/streams/{stream_id}/start`**: Activates live camera reading and tracking.
* **`POST /api/v1/streams/{stream_id}/stop`**: Deactivates the camera stream loop.
* **`WS /api/v1/streams/live/{stream_id}`**: Establishes a WebSocket connection which streams real-time frames with bounding box and trace overlays encoded in Base64 JPEGs.
