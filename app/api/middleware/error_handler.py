"""
error_handler.py — Centralized exception handling middleware for FastAPI.
Formats all exceptions into structured, predictable JSON error responses.
"""

from fastapi import Request, status
from fastapi.responses import JSONResponse
from pydantic import ValidationError as PydanticValidationError

from app.core.exceptions import PlatformException
from app.core.logging import logger


async def platform_exception_handler(request: Request, exc: PlatformException) -> JSONResponse:
    """Handles domain-specific PlatformExceptions."""
    logger.error(
        f"Platform error [{exc.error_code}]: {exc.detail} on {request.method} {request.url.path}",
        extra={"context": exc.context}
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error_code": exc.error_code,
            "message": exc.detail,
            "context": exc.context,
        },
    )


async def pydantic_validation_exception_handler(request: Request, exc: PydanticValidationError) -> JSONResponse:
    """Handles request payload validation errors."""
    logger.warning(f"Validation error on {request.method} {request.url.path}: {exc.errors()}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "error_code": "REQUEST_VALIDATION_ERROR",
            "message": "Invalid request parameters or payload",
            "errors": exc.errors(),
        },
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all for unhandled unexpected exceptions."""
    logger.exception(f"Unhandled server error on {request.method} {request.url.path}: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error_code": "INTERNAL_SERVER_ERROR",
            "message": f"An unexpected error occurred: {str(exc)}",
        },
    )
