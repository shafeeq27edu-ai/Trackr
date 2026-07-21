<#
.SYNOPSIS
    Hybrid development mode: DB + Redis in Docker, Backend + Worker + Frontend run natively.
    This gives the backend direct access to the laptop webcam for live streaming.

.DESCRIPTION
    Docker Desktop on Windows cannot pass USB webcam devices into Linux containers.
    This script starts only the infrastructure (PostgreSQL, Redis) in Docker,
    then runs the FastAPI backend, Celery worker, and Streamlit frontend natively
    on Windows where OpenCV can access the webcam via DirectShow/MSMF.

.NOTES
    Prerequisites:
    - Docker Desktop running (for DB + Redis)
    - Python venv at ./venv with all requirements installed
    - Ports 5432, 6379, 8000, 8501 available

.EXAMPLE
    .\run_dev.ps1
#>

$ErrorActionPreference = "Stop"
$ProjectRoot = $PSScriptRoot

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Trackr - Hybrid Dev Mode (Webcam OK)" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# ── 1. Start infrastructure (DB + Redis) in Docker ──────────────────────────
Write-Host "[1/4] Starting PostgreSQL and Redis in Docker..." -ForegroundColor Yellow
docker compose -f "$ProjectRoot\docker-compose.yml" up -d db redis
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Failed to start Docker infrastructure." -ForegroundColor Red
    exit 1
}

# Wait for DB health
Write-Host "       Waiting for PostgreSQL to be ready..." -ForegroundColor Gray
$retries = 0
do {
    Start-Sleep -Seconds 2
    $retries++
    $health = docker inspect --format='{{.State.Health.Status}}' object-tracker-db-1 2>$null
} while ($health -ne "healthy" -and $retries -lt 15)

if ($health -ne "healthy") {
    Write-Host "ERROR: PostgreSQL did not become healthy in time." -ForegroundColor Red
    exit 1
}
Write-Host "       PostgreSQL is healthy." -ForegroundColor Green

# ── 2. Load environment variables from .env.dev ─────────────────────────────
Write-Host "[2/4] Loading .env.dev environment..." -ForegroundColor Yellow
$envFile = "$ProjectRoot\.env.dev"
if (-not (Test-Path $envFile)) {
    Write-Host "ERROR: .env.dev not found. Please create it first." -ForegroundColor Red
    exit 1
}

Get-Content $envFile | ForEach-Object {
    $line = $_.Trim()
    if ($line -and -not $line.StartsWith("#")) {
        $parts = $line -split "=", 2
        if ($parts.Count -eq 2) {
            [System.Environment]::SetEnvironmentVariable($parts[0].Trim(), $parts[1].Trim(), "Process")
        }
    }
}
# Also set PYTHONPATH so imports work
[System.Environment]::SetEnvironmentVariable("PYTHONPATH", $ProjectRoot, "Process")

Write-Host "       Environment loaded." -ForegroundColor Green

# ── 3. Activate venv ────────────────────────────────────────────────────────
$venvActivate = "$ProjectRoot\venv\Scripts\Activate.ps1"
if (-not (Test-Path $venvActivate)) {
    Write-Host "ERROR: Python venv not found at $ProjectRoot\venv" -ForegroundColor Red
    Write-Host "       Run: python -m venv venv && venv\Scripts\pip install -r requirements.txt" -ForegroundColor Gray
    exit 1
}

Write-Host "[3/4] Activating Python venv..." -ForegroundColor Yellow
& $venvActivate
Write-Host "       Venv activated." -ForegroundColor Green

# ── 4. Run Alembic migrations ───────────────────────────────────────────────
Write-Host "       Running database migrations..." -ForegroundColor Gray
Push-Location $ProjectRoot
try {
    python -m alembic upgrade head 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "       (Alembic migration skipped or not configured - continuing)" -ForegroundColor DarkYellow
    } else {
        Write-Host "       Migrations applied." -ForegroundColor Green
    }
} catch {
    Write-Host "       (Alembic not available - continuing)" -ForegroundColor DarkYellow
}
Pop-Location

# ── 5. Launch services ──────────────────────────────────────────────────────
Write-Host "[4/4] Starting services..." -ForegroundColor Yellow
Write-Host ""

# Start Celery worker in background
Write-Host "  -> Celery Worker (background)" -ForegroundColor Magenta
$workerJob = Start-Job -ScriptBlock {
    param($root, $envFile)
    Set-Location $root
    # Load env vars in this job scope
    Get-Content $envFile | ForEach-Object {
        $line = $_.Trim()
        if ($line -and -not $line.StartsWith("#")) {
            $parts = $line -split "=", 2
            if ($parts.Count -eq 2) {
                [System.Environment]::SetEnvironmentVariable($parts[0].Trim(), $parts[1].Trim(), "Process")
            }
        }
    }
    [System.Environment]::SetEnvironmentVariable("PYTHONPATH", $root, "Process")
    & "$root\venv\Scripts\python.exe" -m celery -A core.execution.worker worker --loglevel=info --pool=threads --concurrency=2
} -ArgumentList $ProjectRoot, $envFile

# Start Streamlit frontend in background
Write-Host "  -> Streamlit Frontend (background, port 8501)" -ForegroundColor Magenta
$frontendJob = Start-Job -ScriptBlock {
    param($root, $envFile)
    Set-Location $root
    Get-Content $envFile | ForEach-Object {
        $line = $_.Trim()
        if ($line -and -not $line.StartsWith("#")) {
            $parts = $line -split "=", 2
            if ($parts.Count -eq 2) {
                [System.Environment]::SetEnvironmentVariable($parts[0].Trim(), $parts[1].Trim(), "Process")
            }
        }
    }
    [System.Environment]::SetEnvironmentVariable("PYTHONPATH", $root, "Process")
    & "$root\venv\Scripts\python.exe" -m streamlit run "$root\frontend\app.py" --server.port 8501 --server.headless true
} -ArgumentList $ProjectRoot, $envFile

Write-Host "  -> FastAPI Backend (foreground, port 8000)" -ForegroundColor Magenta
Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  All services starting!" -ForegroundColor Green
Write-Host "  Backend:  http://localhost:8000" -ForegroundColor White
Write-Host "  Frontend: http://localhost:8501" -ForegroundColor White
Write-Host "  Webcam:   DIRECTLY ACCESSIBLE" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Press Ctrl+C to stop all services." -ForegroundColor DarkYellow
Write-Host ""

# Register cleanup on exit
$null = Register-EngineEvent PowerShell.Exiting -Action {
    Write-Host "`nShutting down background services..." -ForegroundColor Yellow
    Stop-Job -Job $workerJob -ErrorAction SilentlyContinue
    Stop-Job -Job $frontendJob -ErrorAction SilentlyContinue
    Remove-Job -Job $workerJob -Force -ErrorAction SilentlyContinue
    Remove-Job -Job $frontendJob -Force -ErrorAction SilentlyContinue
    Write-Host "Done. Docker infra (db, redis) is still running." -ForegroundColor Gray
    Write-Host "Run 'docker compose down' to stop them too." -ForegroundColor Gray
}

try {
    # Run backend in foreground (Ctrl+C will stop this)
    Push-Location $ProjectRoot
    & "$ProjectRoot\venv\Scripts\python.exe" -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
} finally {
    Pop-Location
    Write-Host "`nStopping background services..." -ForegroundColor Yellow
    Stop-Job -Job $workerJob -ErrorAction SilentlyContinue
    Stop-Job -Job $frontendJob -ErrorAction SilentlyContinue
    Remove-Job -Job $workerJob -Force -ErrorAction SilentlyContinue
    Remove-Job -Job $frontendJob -Force -ErrorAction SilentlyContinue
    Write-Host "All services stopped." -ForegroundColor Green
    Write-Host "Docker infra (db, redis) is still running. Run 'docker compose down' to stop them." -ForegroundColor Gray
}
