import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    environment: str = "development" # development, testing, staging, production
    
    yolo_model_path: str = "yolov8n.pt"
    confidence_threshold: float = 0.3
    hardware_acceleration: str = "auto"
    
    # Storage settings
    storage_provider: str = "local" # local, s3, gcs
    temp_dir: str = "data/temp"
    output_dir: str = "outputs/api"
    
    # Execution settings
    execution_backend: str = "local" # local, celery, ray
    max_workers: int = 4
    
    # Logging
    log_dir: str = "outputs"
    log_level: str = "INFO"
    log_format: str = "text"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

# Load base settings
settings = Settings()

# Support for environment-specific overrides (e.g. .env.production)
env_specific_file = f".env.{settings.environment}"
if os.path.exists(env_specific_file):
    # This allows reloading settings with the specific environment file
    class EnvSpecificSettings(Settings):
        model_config = SettingsConfigDict(env_file=[".env", env_specific_file], env_file_encoding="utf-8", extra="ignore")
    settings = EnvSpecificSettings()
