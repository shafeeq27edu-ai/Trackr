from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    yolo_model_path: str = "yolov8n.pt"
    confidence_threshold: float = 0.3
    hardware_acceleration: str = "auto"
    temp_dir: str = "data/temp"
    output_dir: str = "outputs/api"
    log_dir: str = "outputs"
    log_level: str = "INFO"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
