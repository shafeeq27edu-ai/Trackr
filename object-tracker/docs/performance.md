# Performance & Scaling Guide — Trackr v1.0

This guide outlines performance benchmarks, execution profiles, scaling models, and GPU hardware configurations for Trackr v1.0.

---

## 1. Performance Profiling & Benchmarks

Trackr's core processing loop involves three stages:
1. **Frame Decoding**: Reading frames using OpenCV (`cv2.VideoCapture`).
2. **Model Inference**: Running YOLOv8 object detection on CPU or GPU.
3. **Tracking & Analytics**: Running ByteTrack (IoU overlap) and recording dwell times/statistics.

The table below shows throughput (Frames Per Second) using the default `yolov8n.pt` model across different hardware setups:

| Hardware Configuration | GPU/VRAM | Average FPS | Scaling Limitations |
| :--- | :--- | :--- | :--- |
| **Standard CPU (Intel i7/Ryzen 7)** | None | 8 - 15 FPS | Limited by CPU single-core speed |
| **Apple Silicon (M2 Pro / M3)** | 16GB (Shared) | 25 - 40 FPS | Limited by MPS PyTorch support |
| **Nvidia Tesla T4** | 16GB GDDR6 | 60 - 80 FPS | Balanced entry-level server GPU |
| **Nvidia A10G / A100** | 24GB+ HBM | 150 - 240 FPS | Unlocked high-density workflows |

---

## 2. Hardware Recommendations

### 2.1 Developer Workstation
* **OS**: Linux (Ubuntu 22.04+ recommended) or Windows 11 with WSL2.
* **GPU**: NVIDIA RTX 3060 / 4060 or Apple Silicon Mac.
* **RAM**: 16GB minimum.

### 2.2 Production Staging / VPS
* **Instance Type**: AWS `g4dn.xlarge` (contains 1x Nvidia T4 GPU, 4 vCPUs, 16GB RAM) or GCP `n1-standard-4` + Nvidia T4.
* **Storage**: Persistent SSD with high IOPS for video writing.

---

## 3. Execution Scaling Models

Trackr supports pluggable execution backends to control how concurrent tasks are processed:

### 3.1 Local Execution Backend (Default)
* **Design**: Uses Python `ThreadPoolExecutor` under `core/execution/local.py`.
* **Limits**: Subject to Python's Global Interpreter Lock (GIL). Best for single-node deployments processing 1-4 streams or batch jobs concurrently.
* **VRAM Caution**: Do not run more workers than can fit models in VRAM (each YOLO instance takes ~1GB VRAM).

### 3.2 Distributed Scaling (Celery / Ray)
For high-density workloads (e.g. 50+ concurrent streams):
1. **Queueing**: Offload video jobs to a distributed message queue (Celery + Redis/RabbitMQ).
2. **Worker Nodes**: Spin up GPU worker nodes that pull tasks from the queue, allowing horizontal scaling of CV processing independent of the API server.
3. **Decoupled Storage**: Configure `STORAGE_PROVIDER=s3` or `STORAGE_PROVIDER=gcs` to store source videos and outputs on shared cloud storage instead of local disk.

---

## 4. Key Performance Bottlenecks & Future Work

1. **GIL Constraints**: OpenCV frame reading and numpy annotations are CPU-bound in Python. Future versions will offload frame-writing to native C++ libraries or asynchronous worker threads.
2. **Batching**: Currently, videos are processed frame-by-frame. Implementing tensor batching (e.g., passing 8 frames at a time to the GPU) would increase GPU utilization and yield a 1.5x - 2x speedup on high-end GPUs.
3. **VRAM Churn**: Switching between different models (e.g. YOLOv8n to YOLOv8x) causes VRAM allocation churn. Trackr mitigates this via the `ModelRegistry` lazy loading cache.
