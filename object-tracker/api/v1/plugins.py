from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict, Any
from pydantic import BaseModel
from core.plugin_manager import plugin_manager
from api.deps import get_current_user
from db.models import User

router = APIRouter()


class PluginEnableRequest(BaseModel):
    plugin_name: str
    enable: bool


@router.get("/plugins")
def list_plugins(current_user: User = Depends(get_current_user)):
    """List all discovered plugins."""
    return {"plugins": plugin_manager.list_plugins()}


@router.post("/plugins/enable")
def enable_plugin(request: PluginEnableRequest, current_user: User = Depends(get_current_user)):
    """Enable or disable a plugin (stub for future logic)."""
    # For now, all registered plugins are implicitly enabled.
    plugin = plugin_manager.get_plugin(request.plugin_name)
    if not plugin:
        raise HTTPException(status_code=404, detail="Plugin not found")

    return {
        "status": "success",
        "message": f"Plugin {request.plugin_name} {'enabled' if request.enable else 'disabled'}",
    }
