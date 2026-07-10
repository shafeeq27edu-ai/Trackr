# Security Review — Trackr v1.0

This document contains the security review assessment and recommendations for Trackr v1.0, focusing on protecting access, user assets, and production secrets.

---

## 1. Authentication & Authorization

### 1.1 Authentication Mechanism
* **Standard**: Trackr implements token-based authentication using **JSON Web Tokens (JWT)**.
* **Algorithm**: `HS256` symmetric signing.
* **Token Expiration**: Default is set to 7 days (`10080` minutes).
* **Storage**: In client applications, JWT should be stored in secure cookies (`HttpOnly`, `Secure`, `SameSite=Strict`) to prevent Cross-Site Scripting (XSS) extraction.

### 1.2 Authorization Model
* Users belong to a tenant structure scoped by Projects.
* **Tenant Isolation**: Database queries are filtered by `project_id` and owned `user_id` to prevent cross-tenant exposure of video assets or historical job summaries.
* **System Endpoints**: Resource metrics, hardware configuration, and developer configurations are protected behind a standard authorization middleware check.

---

## 2. Secrets Management

* **Vulnerability Identified**: The project originally contained a hardcoded default signature secret (`SECRET_KEY`).
* **Mitigation (v1.0 GA)**: We updated `core/security.py` to pull the key dynamically from the environment (`os.getenv("SECRET_KEY")`).
* **Deployment Guide**: Ensure your runtime environment passes `SECRET_KEY` as a high-entropy string (e.g. 64 random alphanumeric characters) to the backend. Do not commit `.env` files containing production secrets to code repositories.

---

## 3. Safe Video File Uploads

File uploads are a common vector for remote code execution (RCE) and denial of service (DoS) attacks.
* **Validation Check**: Trackr validates file extensions against an allowed list: `(".mp4", ".avi", ".mov")`.
* **Path Traversal Mitigation**: Uploaded files are renamed using a safe prefix format (`{job_id}_{filename}`) and saved to a dedicated scratch directory (`data/temp/`), preventing directory traversal attacks (e.g. filenames containing `../`).
* **Recommending Max Upload Size**: FastAPI does not limit file upload size by default. It is recommended to configure reverse proxies (Nginx/Cloudflare) to enforce a maximum body size limit (e.g., 500MB) to mitigate storage exhaustion attacks.

---

## 4. Input Validation & SQL Injection

* **ORM Usage**: Trackr uses **SQLAlchemy ORM** to handle all database queries. Raw SQL strings are avoided, preventing SQL injection vulnerabilities.
* **Pydantic Schemas**: All incoming REST request payloads (e.g., login, registration, workspace creations) are strictly validated using Pydantic models. Non-conforming fields are rejected immediately with a `422 Unprocessable Entity` status code.

---

## 5. Security Recommendations for Production

1. **Enable TLS/HTTPS**: Never run the API server or Web UI over HTTP in production. Protect endpoints with Let's Encrypt certificates.
2. **Database Hardening**: While SQLite is suitable for single-host low-load setups, it lacks granular ACLs. Migrate to a secure PostgreSQL service for production scale.
3. **Container Sandbox**: Run Docker containers as non-root users (`USER node` or equivalent in Dockerfile configurations) to prevent container escape exploits.
4. **Regular Dependency Scanning**: Run automatic vulnerability scanners (e.g., `pip-audit`, `snyk`) on your CI/CD pipeline.
