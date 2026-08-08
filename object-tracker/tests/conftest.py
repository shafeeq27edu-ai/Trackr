import os
import shutil

import pytest
from fastapi.testclient import TestClient

os.environ["SECRET_KEY"] = "test-secret-key-that-is-long-enough-and-secure"


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
    from api.deps import get_current_user
    from db.models import User

    # Override get_current_user to bypass authentication in tests
    dummy_user = User(id="test-user-id", email="test@example.com", name="Test User")
    app.dependency_overrides[get_current_user] = lambda: dummy_user

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
def test_db():
    import asyncio
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
    from db.database import Base

    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    
    async def init_db():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            
    asyncio.run(init_db())
    
    SessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    session = SessionLocal()
    yield session
    
    asyncio.run(session.close())


@pytest.fixture
def auth_client(test_db):
    from db.database import get_db
    
    async def override_get_db():
        yield test_db

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
