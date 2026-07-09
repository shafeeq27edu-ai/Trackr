from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from db.database import get_db
from core.dependencies import get_detector
from tracker.detector import YoloDetector
from core.logging import logger

router = APIRouter()

@router.get("/health")
def health_check():
    """Basic alive ping for load balancers."""
    return {"status": "ok"}

@router.get("/ready")
def readiness_check(
    db: Session = Depends(get_db),
    detector: YoloDetector = Depends(get_detector)
):
    """
    Check if the application is ready to accept traffic.
    Verifies database connectivity and model loading.
    """
    try:
        # Check Database
        db.execute(text("SELECT 1"))
    except Exception as e:
        logger.error(f"Readiness check failed - DB error: {e}")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database not ready")
        
    try:
        # Check Model
        if not detector.model:
            raise Exception("Model not loaded")
    except Exception as e:
        logger.error(f"Readiness check failed - Model error: {e}")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Model not ready")
        
    return {"status": "ready"}

@router.get("/live")
def liveness_check():
    """Container lifecycle check."""
    return {"status": "alive"}
