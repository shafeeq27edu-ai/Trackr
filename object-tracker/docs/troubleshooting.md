# Troubleshooting Guide — Trackr v1.0

This guide provides resolutions for common issues encountered during setup, runtime, or upgrades of Trackr v1.0.

---

## 1. Installation and Boot Errors

### 1.1 `ModuleNotFoundError: No module named 'cv2'`
* **Cause**: OpenCV dependencies were not fully installed in the active virtual environment.
* **Resolution**: Re-run dependency installer inside virtual environment:
  ```bash
  pip install -r requirements.txt
  ```

### 1.2 Database Migration Failures (`alembic.util.exc.CommandError`)
* **Cause**: Active database file (`trackr.db`) has schemas that drift from migration history, or migration folder has conflicting revisions.
* **Resolution**:
  1. If running in development, safety-delete the sqlite file and migration cache:
     ```bash
     rm trackr.db
     alembic upgrade head
     ```
  2. If running in production, restore database from backup, or run:
     ```bash
     alembic stamp head
     ```

---

## 2. API and Stream Failures

### 2.1 WebSocket Disconnects on Live Video Stream
* **Cause**: Network middleware, reverse proxy timeout limits, or client-side frames rendering slower than production speed.
* **Resolution**:
  1. Check Nginx buffer configuration to ensure it supports persistent connections (Upgrade headers).
  2. Reduce stream resolution or skip frames to lower client-side latency.

### 2.2 `sqlite3.OperationalError: database is locked`
* **Cause**: High write load on SQLite exceeds sequential locking capability.
* **Resolution**:
  1. Verify database queries close sessions correctly.
  2. In production, change the SQL URL in settings to point to a highly-available **PostgreSQL** instance.
