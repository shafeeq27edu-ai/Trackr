from fastapi import FastAPI
from contextlib import asynccontextmanager
from config.settings import settings

from core.logging import logger
from core.exceptions import TrackrException, trackr_exception_handler, global_exception_handler
from core.job_manager import JobManager
from api.v1 import jobs, system, streams, auth, projects, health
from prometheus_fastapi_instrumentator import Instrumentator

from core.model_manager import ModelManager

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI Lifespan event handler.
    Initializes heavy models once on startup and makes them globally accessible via app.state.
    """
    logger.info("Initializing application startup sequence...")
    
    try:
        # Load the ModelManager exactly once!
        model_manager = ModelManager()
        # Pre-load the configured model
        model_manager.get_yolo_model(settings.yolo_model_path)
        
        app.state.model_manager = model_manager
        app.state.settings = settings
        app.state.job_manager = JobManager()
        from core.stream_manager import StreamManager
        app.state.stream_manager = StreamManager()
        logger.info("ModelManager, JobManager, and StreamManager loaded successfully. Ready to serve requests.")
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
app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(projects.router, prefix="/api/v1/projects", tags=["projects"])
app.include_router(jobs.router, prefix="/api/v1", tags=["jobs"])
app.include_router(system.router, prefix="/api/v1/system", tags=["system"])
app.include_router(health.router, prefix="/api/v1/system", tags=["health"])

# Mount Prometheus metrics
Instrumentator().instrument(app).expose(app)
