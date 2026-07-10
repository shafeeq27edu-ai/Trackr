from abc import ABC, abstractmethod
from typing import BinaryIO, Optional

class StorageProvider(ABC):
    """Abstract base class for storage providers."""

    @abstractmethod
    def save(self, file_path: str, data: BinaryIO) -> str:
        """Saves a file to storage and returns a reference path or URL."""
        pass

    @abstractmethod
    def get(self, file_path: str) -> BinaryIO:
        """Retrieves a file from storage as a binary stream."""
        pass

    @abstractmethod
    def exists(self, file_path: str) -> bool:
        """Checks if a file exists in storage."""
        pass

    @abstractmethod
    def get_url(self, file_path: str) -> Optional[str]:
        """Returns a publicly accessible URL if supported."""
        pass

    @abstractmethod
    def get_local_path(self, file_path: str) -> Optional[str]:
        """Returns a local file path if the storage is local or downloaded."""
        pass
