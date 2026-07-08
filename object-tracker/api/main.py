from fastapi import FastAPI
from contextlib import asynccontextmanager
from config.settings import settings
from tracker.detector import YoloDetector
from core.logging import logger
from core.exceptions import TrackrException, trackr_exception_handler, global_exception_handler
from core.job_manager import JobManager
from api.v1 import jobs

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI Lifespan event handler.
    Initializes heavy models once on startup and makes them globally accessible via app.state.
    """
    logger.info("Initializing application startup sequence...")
    logger.info(f"Loading YOLO model from: {settings.yolo_model_path}")
    
    try:
        # Load the heavy model exactly once!
        detector = YoloDetector(settings.yolo_model_path)
        app.state.detector = detector
        app.state.settings = settings
        app.state.job_manager = JobManager()
        logger.info("Model and JobManager loaded successfully. Ready to serve requests.")
    except Exception as e:
        logger.critical(f"Failed to initialize model during startup: {str(e)}", exc_info=True)
        raise e
        
    yield
    
    logger.info("Application shutdown sequence initiated.")
    # Add any cleanup logic here

app = FastAPI(
    title="Trackr API", 
    description="Computer Vision Object Tracking Backend",
    version="1.0.0",
    lifespan=lifespan
)

# Register Custom Exception Handlers
app.add_exception_handler(TrackrException, trackr_exception_handler)
app.add_exception_handler(Exception, global_exception_handler)

# Register API Routers
app.include_router(jobs.router, prefix="/api/v1", tags=["jobs"])
