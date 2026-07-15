import asyncio
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from typing import Dict, Any, List

from core.stream_manager import StreamManager, StreamStatus
from core.dependencies import get_stream_manager, get_detector
from tracker.detector import YoloDetector
from services.stream_service import process_live_stream
from core.logging import logger
from api.deps import get_current_user
from db.models import User

router = APIRouter()


class StreamCreateRequest(BaseModel):
    source: str


@router.post("")
def create_stream(
    request: StreamCreateRequest,
    stream_manager: StreamManager = Depends(get_stream_manager),
    current_user: User = Depends(get_current_user),
):
    stream = stream_manager.create_stream(request.source)
    return {"id": stream.id, "source": stream.source, "status": stream.status}


@router.get("")
def list_streams(
    stream_manager: StreamManager = Depends(get_stream_manager),
    current_user: User = Depends(get_current_user),
):
    streams = stream_manager.list_streams()
    return {"streams": [s.model_dump() for s in streams.values()]}


@router.get("/{stream_id}")
def get_stream(
    stream_id: str,
    stream_manager: StreamManager = Depends(get_stream_manager),
    current_user: User = Depends(get_current_user),
):
    stream = stream_manager.get_stream(stream_id)
    if not stream:
        raise HTTPException(status_code=404, detail="Stream not found")
    return stream.model_dump()


@router.post("/{stream_id}/start")
async def start_stream(
    stream_id: str,
    stream_manager: StreamManager = Depends(get_stream_manager),
    detector: YoloDetector = Depends(get_detector),
    current_user: User = Depends(get_current_user),
):
    stream = stream_manager.get_stream(stream_id)
    if not stream:
        raise HTTPException(status_code=404, detail="Stream not found")

    if stream.status == StreamStatus.PLAYING:
        return {"message": "Stream is already playing"}

    stream.stop_event = asyncio.Event()

    # Launch in asyncio task
    task = asyncio.create_task(
        process_live_stream(stream_id, stream.source, stream_manager, detector)
    )
    stream.task = task

    return {"message": "Stream started", "id": stream_id}


@router.post("/{stream_id}/stop")
def stop_stream(
    stream_id: str,
    stream_manager: StreamManager = Depends(get_stream_manager),
    current_user: User = Depends(get_current_user),
):
    stream = stream_manager.get_stream(stream_id)
    if not stream:
        raise HTTPException(status_code=404, detail="Stream not found")

    if stream.stop_event:
        stream.stop_event.set()

    stream_manager.update_stream(stream_id, status=StreamStatus.STOPPED)
    return {"message": "Stream stop signal sent"}


@router.delete("/{stream_id}")
def delete_stream(
    stream_id: str,
    stream_manager: StreamManager = Depends(get_stream_manager),
    current_user: User = Depends(get_current_user),
):
    if stream_manager.remove_stream(stream_id):
        return {"message": "Stream deleted"}
    raise HTTPException(status_code=404, detail="Stream not found")


@router.post("/{stream_id}/record")
def record_stream(
    stream_id: str,
    stream_manager: StreamManager = Depends(get_stream_manager),
    current_user: User = Depends(get_current_user),
):
    stream = stream_manager.get_stream(stream_id)
    if not stream:
        raise HTTPException(status_code=404, detail="Stream not found")

    import os

    os.makedirs("outputs/live_recordings", exist_ok=True)
    recording_path = (
        f"outputs/live_recordings/recording_{stream_id}_{int(asyncio.get_event_loop().time())}.mp4"
    )

    stream_manager.update_stream(stream_id, is_recording=True, recording_path=recording_path)
    return {"message": "Recording started", "path": recording_path}


@router.post("/{stream_id}/stop_record")
def stop_record_stream(
    stream_id: str,
    stream_manager: StreamManager = Depends(get_stream_manager),
    current_user: User = Depends(get_current_user),
):
    stream = stream_manager.get_stream(stream_id)
    if not stream:
        raise HTTPException(status_code=404, detail="Stream not found")

    stream_manager.update_stream(stream_id, is_recording=False)
    return {"message": "Recording stopped", "path": stream.recording_path}


# --- WebSockets ---


@router.websocket("/live/{stream_id}")
async def websocket_live_stream(
    websocket: WebSocket,
    stream_id: str,
    token: str = None,
    stream_manager: StreamManager = Depends(get_stream_manager),
):
    if not token:
        await websocket.close(code=4001, reason="Unauthorized")
        return

    try:
        from core.security import SECRET_KEY, ALGORITHM
        import jwt

        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if not payload.get("user_id"):
            await websocket.close(code=4001, reason="Unauthorized")
            return
    except Exception:
        await websocket.close(code=4001, reason="Unauthorized")
        return

    stream = stream_manager.get_stream(stream_id)
    if not stream:
        await websocket.close(code=4004, reason="Stream not found")
        return

    await stream_manager.connect_client(websocket, stream_id)

    try:
        while True:
            # Keep connection alive, wait for client disconnect
            # We don't necessarily need to read from client, but we must yield to the event loop
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        stream_manager.disconnect_client(websocket, stream_id)
        logger.info(f"Client disconnected from stream {stream_id}")
    except Exception as e:
        stream_manager.disconnect_client(websocket, stream_id)


@router.websocket("/status")
async def websocket_global_status(
    websocket: WebSocket, stream_manager: StreamManager = Depends(get_stream_manager)
):
    await stream_manager.connect_status_client(websocket)
    try:
        while True:
            # We can use this endpoint to periodically broadcast all streams' statuses
            await stream_manager.broadcast_status()
            await asyncio.sleep(2)  # Broadast every 2 seconds

            # This try block just listens to ensure connection is alive, though wait_for is better
            # We'll just wait here until disconnect
    except WebSocketDisconnect:
        stream_manager.disconnect_status_client(websocket)
    except Exception:
        stream_manager.disconnect_status_client(websocket)
