
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from api.deps import get_current_user
from core.models.registry import model_registry
from db.models import User

router = APIRouter()


class ModelLoadRequest(BaseModel):
    model_id: str


@router.get("/models")
def list_models(current_user: User = Depends(get_current_user)):
    """List all available models in the registry."""
    return {"models": model_registry.get_available_models()}


@router.post("/models/load")
def load_model(request: ModelLoadRequest, current_user: User = Depends(get_current_user)):
    """Preloads a model into memory."""
    try:
        model_registry.get_model(request.model_id)
        return {"status": "success", "message": f"Model {request.model_id} loaded successfully"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load model: {str(e)}")
