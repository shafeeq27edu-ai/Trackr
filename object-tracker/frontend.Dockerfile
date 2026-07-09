FROM python:3.11-slim

WORKDIR /app

# Copy requirements and install
# Note: In production we could split frontend and backend requirements,
# but using the same for simplicity in this mono-repo setup.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose Streamlit port
EXPOSE 8501

# Run Streamlit
CMD ["streamlit", "run", "frontend/app.py", "--server.port", "8501", "--server.address", "0.0.0.0"]
