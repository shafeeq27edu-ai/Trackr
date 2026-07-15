# syntax=docker/dockerfile:1
FROM python:3.11-slim

WORKDIR /app

# Pre-install heavy dependencies with CPU-only wheels to avoid CUDA bloat
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu

# Copy requirements and install remaining
# Note: In production we could split frontend and backend requirements,
# but using the same for simplicity in this mono-repo setup.
COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt

# Copy application code
COPY . .

# Expose Streamlit port
EXPOSE 8501

# Run Streamlit
CMD ["streamlit", "run", "frontend/app.py", "--server.port", "8501", "--server.address", "0.0.0.0"]
