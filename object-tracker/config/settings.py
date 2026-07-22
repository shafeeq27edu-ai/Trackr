import os
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    environment: str = Field("development", description="development, testing, staging, production")

    yolo_model_path: str = Field("yolov8s.pt", description="Path to YOLO model")
    confidence_threshold: float = Field(0.3, ge=0.0, le=1.0)
    hardware_acceleration: str = "auto"

    # Storage settings
    storage_provider: str = Field("local", description="local, s3, gcs")
    temp_dir: str = "data/temp"
    output_dir: str = "outputs/api"

    # Execution settings
    execution_backend: str = Field("local", description="local, celery, ray")
    max_workers: int = Field(4, gt=0)

    # Logging
    log_dir: str = "outputs"
    log_level: str = "INFO"
    log_format: str = "text"

    # Infrastructure (Postgres & Redis)
    database_url: str = Field(
        "sqlite+aiosqlite:///trackr.db", description="PostgreSQL Async Connection URL"
    )
    redis_url: str = Field("redis://localhost:6379/0", description="Redis Broker URL")

    # Model Cache
    max_cached_models: int = Field(2, gt=0)

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache()
def get_cached_settings() -> Settings:
    """Returns a cached instance of the settings."""
    settings = Settings()
    env_specific_file = f".env.{settings.environment}"
    if os.path.exists(env_specific_file):

        class EnvSpecificSettings(Settings):
            model_config = SettingsConfigDict(
                env_file=[".env", env_specific_file], env_file_encoding="utf-8", extra="ignore"
            )

        return EnvSpecificSettings()
    return settings


settings = get_cached_settings()
