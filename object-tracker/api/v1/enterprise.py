from fastapi import APIRouter, Depends

from api.deps import get_current_user
from config.settings import settings
from core.events import EventType, event_bus
from core.storage.manager import storage_manager
from db.models import User

router = APIRouter()

# Keep a simple history of events for the API
_event_history = []


def _capture_event(payload):
    _event_history.append(payload)
    if len(_event_history) > 100:
        _event_history.pop(0)


# Subscribe to some events
# Note: we pass dummy functions since EventBus accepts (payload)
event_bus.subscribe(
    EventType.JOB_CREATED, lambda p: _capture_event({"type": "JobCreated", "payload": p})
)
event_bus.subscribe(
    EventType.JOB_STARTED, lambda p: _capture_event({"type": "JobStarted", "payload": p})
)
event_bus.subscribe(
    EventType.JOB_COMPLETED, lambda p: _capture_event({"type": "JobCompleted", "payload": p})
)
event_bus.subscribe(
    EventType.PLUGIN_LOADED, lambda p: _capture_event({"type": "PluginLoaded", "payload": p})
)
event_bus.subscribe(
    EventType.MODEL_LOADED, lambda p: _capture_event({"type": "ModelLoaded", "payload": p})
)


@router.get("/system/events")
def list_events(current_user: User = Depends(get_current_user)):
    """List recent system events."""
    return {"events": _event_history}


@router.get("/system/storage")
def get_storage_info(current_user: User = Depends(get_current_user)):
    """Get current storage configuration."""
    provider = storage_manager.get_provider()
    return {"provider": provider.__class__.__name__, "configured_type": settings.storage_provider}
