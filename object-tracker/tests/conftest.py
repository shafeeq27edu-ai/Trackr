import pytest
import os
import shutil
from fastapi.testclient import TestClient
from api.main import app
from config.settings import Settings
from core.job_manager import JobManager

@pytest.fixture
def mock_settings():
    # Provide safe testing paths that don't overwrite real data
    os.environ["TRACKR_LOG_DIR"] = "tests/test_outputs/logs"
    os.environ["TRACKR_OUTPUT_DIR"] = "tests/test_outputs/outputs"
    os.environ["TRACKR_TEMP_DIR"] = "tests/test_outputs/temp"
    
    settings = Settings()
    os.makedirs(settings.log_dir, exist_ok=True)
    os.makedirs(settings.output_dir, exist_ok=True)
    os.makedirs(settings.temp_dir, exist_ok=True)
    
    yield settings
    
    # Cleanup after test
    shutil.rmtree("tests/test_outputs", ignore_errors=True)

@pytest.fixture
def job_manager():
    return JobManager()

@pytest.fixture
def client():
    # TestClient will automatically call startup/shutdown lifespan events
    with TestClient(app) as test_client:
        yield test_client
