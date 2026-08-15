import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from fastapi import WebSocket
from pydantic import BaseModel, Field


class StreamStatus(str, Enum):
    INITIALIZING = "INITIALIZING"
    PLAYING = "PLAYING"
    PAUSED = "PAUSED"
    STOPPED = "STOPPED"
    FAILED = "FAILED"


class LiveStream(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source: str
    user_id: str
    status: StreamStatus = StreamStatus.INITIALIZING
    fps: float = 0.0
    resolution: Optional[str] = None
    start_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    uptime: float = 0.0
    error: Optional[str] = None
    is_recording: bool = False
    recording_path: Optional[str] = None

    # Enhanced Metrics
    frames_processed: int = 0
    camera_connected: bool = False
    active_websocket_clients: int = 0
    total_detections: int = 0

    # Non-pydantic fields
    task: Optional[Any] = Field(default=None, exclude=True)
    stop_event: Optional[Any] = Field(default=None, exclude=True)


class StreamManager:
    """Manages active live streams and their connected WebSocket clients."""

    def __init__(self):
        self._streams: Dict[str, LiveStream] = {}
        # Mapping stream_id -> list of connected WebSockets
        self._active_connections: Dict[str, List[WebSocket]] = {}
        self._status_connections: Dict[str, List[WebSocket]] = {}

    def create_stream(self, source: str, user_id: str) -> LiveStream:
        stream = LiveStream(source=source, user_id=user_id)
        self._streams[stream.id] = stream
        self._active_connections[stream.id] = []
        return stream

    def get_stream(self, stream_id: str) -> Optional[LiveStream]:
        return self._streams.get(stream_id)

    def list_streams(self) -> Dict[str, LiveStream]:
        return self._streams

    def get_active_streams(self) -> List[LiveStream]:
        """Return streams that are currently playing."""
        return [s for s in self._streams.values() if s.status == StreamStatus.PLAYING]

    @property
    def active_connections(self) -> Dict[str, List[WebSocket]]:
        """Public read-only access to the active WebSocket connections."""
        return self._active_connections

    def update_stream(self, stream_id: str, **kwargs):
        stream = self._streams.get(stream_id)
        if not stream:
            return None

        for key, value in kwargs.items():
            if hasattr(stream, key):
                setattr(stream, key, value)

        if "status" in kwargs and stream.status in [StreamStatus.PLAYING]:
            stream.uptime = (datetime.now(timezone.utc) - stream.start_time).total_seconds()

        return stream

    def remove_stream(self, stream_id: str) -> bool:
        if stream_id in self._streams:
            stream = self._streams[stream_id]
            if stream.stop_event:
                stream.stop_event.set()
            del self._streams[stream_id]
            # Connections should close automatically when they fail to receive data
            # or check stream existence
            if stream_id in self._active_connections:
                del self._active_connections[stream_id]
            return True
        return False

    # --- WebSocket Management ---

    async def connect_client(self, websocket: WebSocket, stream_id: str):
        await websocket.accept()
        if stream_id not in self._active_connections:
            self._active_connections[stream_id] = []
        self._active_connections[stream_id].append(websocket)

        # Update metrics
        if stream_id in self._streams:
            self._streams[stream_id].active_websocket_clients = len(
                self._active_connections[stream_id]
            )

    def disconnect_client(self, websocket: WebSocket, stream_id: str):
        if (
            stream_id in self._active_connections
            and websocket in self._active_connections[stream_id]
        ):
            self._active_connections[stream_id].remove(websocket)

            # Update metrics
            if stream_id in self._streams:
                self._streams[stream_id].active_websocket_clients = len(
                    self._active_connections[stream_id]
                )

    async def broadcast_to_stream(self, stream_id: str, message: dict):
        if stream_id in self._active_connections:
            # Create a copy of the list to avoid modification during iteration
            for connection in list(self._active_connections[stream_id]):
                try:
                    await connection.send_json(message)
                except Exception:
                    self.disconnect_client(connection, stream_id)

    async def broadcast_bytes_to_stream(self, stream_id: str, data: bytes):
        if stream_id in self._active_connections:
            for connection in list(self._active_connections[stream_id]):
                try:
                    await connection.send_bytes(data)
                except Exception:
                    self.disconnect_client(connection, stream_id)

    async def connect_status_client(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        if user_id not in self._status_connections:
            self._status_connections[user_id] = []
        self._status_connections[user_id].append(websocket)

    def disconnect_status_client(self, websocket: WebSocket, user_id: str):
        if user_id in self._status_connections and websocket in self._status_connections[user_id]:
            self._status_connections[user_id].remove(websocket)

    async def broadcast_status(self, user_id: str):
        """Broadcasts the status of user's streams to status clients."""
        if user_id not in self._status_connections or not self._status_connections[user_id]:
            return

        data = {s_id: stream.model_dump() for s_id, stream in self._streams.items() if stream.user_id == user_id}
        for connection in list(self._status_connections[user_id]):
            try:
                await connection.send_json(data)
            except Exception:
                self.disconnect_status_client(connection, user_id)
