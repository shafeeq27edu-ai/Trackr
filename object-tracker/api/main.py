from fastapi import FastAPI
from contextlib import asynccontextmanager
from config.settings import settings

from core.logging import logger
from core.exceptions import TrackrException
from core.job_manager import JobManager
from api.v1 import jobs, system, streams, auth, projects, health, models, plugins, enterprise
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
        # Discover plugins and models
        from core.plugin_manager import plugin_manager
        from core.models.registry import model_registry

        plugin_manager.discover_plugins()
        model_registry.discover_from_plugins()

        # Load the ModelManager exactly once!
        from core.dependencies import get_model_manager, get_settings

        # Pre-load the configured model
        model_manager = get_model_manager()
        model_manager.get_yolo_model(get_settings().yolo_model_path)

        logger.info(
            "ModelManager, JobManager, and StreamManager loaded successfully. Ready to serve requests."
        )
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
    lifespan=lifespan,
)

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from core.exceptions import (
    TrackrException,
    trackr_exception_handler,
    global_exception_handler,
    http_exception_handler,
    request_validation_exception_handler,
)
from fastapi import HTTPException
from fastapi.exceptions import RequestValidationError

# Register Custom Exception Handlers
app.add_exception_handler(TrackrException, trackr_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, request_validation_exception_handler)
app.add_exception_handler(Exception, global_exception_handler)

# Register API Routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(projects.router, prefix="/api/v1/projects", tags=["projects"])
app.include_router(jobs.router, prefix="/api/v1", tags=["jobs"])
app.include_router(system.router, prefix="/api/v1/system", tags=["system"])
app.include_router(health.router, prefix="/api/v1/system", tags=["health"])
app.include_router(models.router, prefix="/api/v1", tags=["models"])
app.include_router(plugins.router, prefix="/api/v1", tags=["plugins"])
app.include_router(enterprise.router, prefix="/api/v1", tags=["enterprise"])
app.include_router(streams.router, prefix="/api/v1/streams", tags=["streams"])

# Mount Prometheus metrics
Instrumentator().instrument(app).expose(app)
