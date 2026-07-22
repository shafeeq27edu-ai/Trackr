import logging

from config.settings import settings
from core.storage.base import StorageProvider
from core.storage.local import LocalStorageProvider

logger = logging.getLogger(__name__)


class StorageManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(StorageManager, cls).__new__(cls)
            cls._instance.provider = cls._instance._init_provider()
        return cls._instance

    def _init_provider(self) -> StorageProvider:
        # Currently we only support local, but we can extend this using settings
        # e.g., if settings.storage_type == "s3": return S3StorageProvider()
        logger.info(f"Initializing LocalStorageProvider at {settings.output_dir}")
        return LocalStorageProvider(base_dir=settings.output_dir)

    def get_provider(self) -> StorageProvider:
        return self.provider


storage_manager = StorageManager()
