import asyncio
import websockets
import json
from typing import Callable, Any


class TrackrStreamClient:
    """WebSocket Client for real-time Trackr streams."""

    def __init__(self, ws_url: str = "ws://localhost:8000"):
        self.ws_url = ws_url.rstrip("/")

    async def connect_and_listen(self, stream_id: str, callback: Callable[[dict], Any]):
        """Connects to a tracking stream and invokes the callback on each frame data."""
        url = f"{self.ws_url}/api/v1/streams/{stream_id}/ws"
        async with websockets.connect(url) as websocket:
            try:
                async for message in websocket:
                    data = json.loads(message)
                    callback(data)
            except websockets.exceptions.ConnectionClosed:
                print("Stream connection closed.")
