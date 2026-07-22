import os
import shutil
from typing import BinaryIO, Optional

from core.logging import logger
from core.storage.base import StorageProvider


class LocalStorageProvider(StorageProvider):
    """Local filesystem storage provider."""

    def __init__(self, base_dir: str = "."):
        self.base_dir = os.path.abspath(base_dir)
        os.makedirs(self.base_dir, exist_ok=True)

    def _get_full_path(self, file_path: str) -> str:
        # Prevent directory traversal
        full_path = os.path.abspath(os.path.join(self.base_dir, file_path))
        if not full_path.startswith(self.base_dir):
            raise ValueError("Invalid file path")
        return full_path

    def save(self, file_path: str, data: BinaryIO) -> str:
        full_path = self._get_full_path(file_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "wb") as f:
            shutil.copyfileobj(data, f)
        logger.debug(f"Saved file to local storage: {full_path}")
        return file_path

    def get(self, file_path: str) -> BinaryIO:
        full_path = self._get_full_path(file_path)
        if not os.path.exists(full_path):
            raise FileNotFoundError(f"File not found: {full_path}")
        return open(full_path, "rb")

    def exists(self, file_path: str) -> bool:
        return os.path.exists(self._get_full_path(file_path))

    def get_url(self, file_path: str) -> Optional[str]:
        # Local storage might not have a direct URL unless served by an HTTP server
        return None

    def get_local_path(self, file_path: str) -> Optional[str]:
        return self._get_full_path(file_path)
