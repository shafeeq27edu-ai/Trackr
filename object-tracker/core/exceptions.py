from fastapi import Request, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from core.logging import logger


class TrackrException(Exception):
    """Base exception for Trackr application."""

    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class UnsupportedFormatError(TrackrException):
    def __init__(self, message: str = "Unsupported file format."):
        super().__init__(message, status_code=400)


class VideoProcessingError(TrackrException):
    def __init__(self, message: str = "Failed to process video."):
        super().__init__(message, status_code=500)


class ModelLoadingError(TrackrException):
    def __init__(self, message: str = "Failed to load the model."):
        super().__init__(message, status_code=500)


async def trackr_exception_handler(request: Request, exc: TrackrException):
    logger.error(f"TrackrException occurred: {exc.message} (Status: {exc.status_code})")
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": True, "message": exc.message},
    )


async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": True, "message": exc.detail},
    )


async def request_validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = [{"loc": err["loc"], "msg": err["msg"], "type": err["type"]} for err in exc.errors()]
    return JSONResponse(
        status_code=422,
        content={"error": True, "message": "Validation Error", "details": errors},
    )


async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled Exception occurred: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": True, "message": "An unexpected internal server error occurred."},
    )
