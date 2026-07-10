# Installation Guide — Trackr v1.0

This guide walks you through setting up Trackr v1.0 on your local machine or server.

---

## Prerequisites
* **Python**: Version `3.10` or `3.11`.
* **System Dependencies**: OpenCV requires certain graphics libraries on Linux:
  ```bash
  sudo apt-get update && sudo apt-get install -y libgl1-mesa-glx libglib2.0-0
  ```

---

## 1. Setup Environment

1. Clone the repository:
   ```bash
   git clone https://github.com/trackr/trackr.git
   cd trackr
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   ```

3. Activate the virtual environment:
   - **Linux/macOS**:
     ```bash
     source venv/bin/activate
     ```
   - **Windows**:
     ```powershell
     .\venv\Scripts\Activate.ps1
     ```

4. Install the pinned dependencies:
   ```bash
   pip install --upgrade pip
   pip install -r object-tracker/requirements.txt
   ```

---

## 2. Configuration Settings

1. Copy the template environment file:
   ```bash
   cp object-tracker/.env.example object-tracker/.env
   ```

2. Edit `object-tracker/.env` to configure your settings:
   - **`SECRET_KEY`**: Set a unique secret token for authentication.
   - **`ENVIRONMENT`**: Set to `development` or `production`.
   - **`HARDWARE_ACCELERATION`**: Set to `auto`, `cuda`, `mps`, or `cpu`.

---

## 3. Database Initialization

Trackr uses **Alembic** to manage SQLite database schemas. Initialize and run migrations:

```bash
cd object-tracker
alembic upgrade head
```

This creates a local `trackr.db` file containing user, project, and job metadata.
