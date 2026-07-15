# syntax=docker/dockerfile:1
FROM python:3.11-slim

# Install system dependencies for OpenCV and ByteTrack
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Pre-install heavy dependencies with CPU-only wheels to avoid CUDA bloat
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu

# Copy requirements and install remaining (using cache mount instead of --no-cache-dir)
COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt
RUN pip install email-validator
# Copy application code
COPY . .

# Expose FastAPI port
EXPOSE 8000

# Run FastAPI server
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
