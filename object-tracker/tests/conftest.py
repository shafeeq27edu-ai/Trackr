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

    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

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


@pytest.fixture
def real_auth_client(auth_client):
    """
    A test client that creates a real user in the test database,
    logs in, and sets the Authorization header with a real JWT.
    """
    user_data = {
        "email": "realuser@example.com",
        "password": "securepassword123",
        "name": "Real User",
    }

    # Register
    res = auth_client.post("/api/v1/auth/register", json=user_data)
    assert res.status_code in (200, 201)

    # Login
    login_res = auth_client.post(
        "/api/v1/auth/login",
        data={"username": user_data["email"], "password": user_data["password"]},
    )
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]

    auth_client.headers.update({"Authorization": f"Bearer {token}"})
    yield auth_client


@pytest.fixture
def user_factory(auth_client):
    """
    Factory fixture to create multiple real users for cross-user tests.
    Returns a function that creates a user and returns their token and ID.
    """

    def _create_user(email: str, password: str = "securepassword123"):
        user_data = {"email": email, "password": password, "name": "Test User"}
        res = auth_client.post("/api/v1/auth/register", json=user_data)
        assert res.status_code in (200, 201)

        login_res = auth_client.post(
            "/api/v1/auth/login", data={"username": email, "password": password}
        )
        assert login_res.status_code == 200
        token = login_res.json()["access_token"]

        me_res = auth_client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert me_res.status_code == 200
        user_id = me_res.json()["id"]

        return {"token": token, "user_id": user_id, "email": email}

    return _create_user
