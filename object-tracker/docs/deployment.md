# Production Deployment Guide — Trackr v1.0

This guide details steps for deploying Trackr v1.0 in a secure, containerized production environment.

---

## 1. Single-Node Docker Compose (Recommended)

Docker Compose orchestrates the Backend (FastAPI) and Frontend (Streamlit) services in an isolated virtual network.

### 1.1 Environment Setup (`.env`)
Create a production environment file:
```ini
ENVIRONMENT=production
SECRET_KEY=y0ur_sup3r_s3cr3t_jwt_s1gn1ng_key_h3r3
HARDWARE_ACCELERATION=auto  # uses CUDA if Nvidia Docker Toolkit is active, else CPU
STORAGE_PROVIDER=local
LOG_FORMAT=json
LOG_LEVEL=INFO
```

### 1.2 Run Services
Rebuild and launch:
```bash
docker compose up -d --build
```
This binds:
* FastAPI to `http://localhost:8000`
* Streamlit to `http://localhost:8501`

---

## 2. Production Security Checklist

* **Enable SSL/TLS**: Place an Nginx, Caddy, or Cloudflare reverse proxy in front of the services.
* **Database Volumes**: Ensure the SQLite database file (`trackr.db`) is mounted on a persistent SSD volume (e.g. AWS EBS).
* **Upload Storage Size**: By default, uploads are stored locally. Configure persistent storage directories to prevent the container disk from filling up.
* **Environment-Specific Secrets**: Never commit `.env` files. Inject them using environment variable configuration panels in your cloud dashboard.
* **Firewall Access**: Only expose the Reverse Proxy ports (`80`, `443`) to the public. Restrict direct access to port `8000` and `8501`.
