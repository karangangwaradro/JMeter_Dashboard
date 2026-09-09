"""
exceptions.py — Explicit application and domain exceptions for PerfPilot.
"""

from typing import Any, Dict, Optional


class PlatformException(Exception):
    """Base exception for all PerfPilot errors."""

    def __init__(
        self,
        detail: str,
        error_code: str = "PLATFORM_ERROR",
        status_code: int = 500,
        context: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(detail)
        self.detail = detail
        self.error_code = error_code
        self.status_code = status_code
        self.context = context or {}


class TestExecutionError(PlatformException):
    """Raised when starting, executing, or stopping a test fails."""

    def __init__(self, detail: str, context: Optional[Dict[str, Any]] = None):
        super().__init__(
            detail=detail,
            error_code="TEST_EXECUTION_ERROR",
            status_code=500,
            context=context,
        )


class ResultCollectionError(PlatformException):
    """Raised when fetching or downloading raw test results fails."""

    def __init__(self, detail: str, context: Optional[Dict[str, Any]] = None):
        super().__init__(
            detail=detail,
            error_code="RESULT_COLLECTION_ERROR",
            status_code=502,
            context=context,
        )


class ParserError(PlatformException):
    """Raised when converting native tool outputs to domain models fails."""

    def __init__(self, detail: str, context: Optional[Dict[str, Any]] = None):
        super().__init__(
            detail=detail,
            error_code="PARSER_ERROR",
            status_code=422,
            context=context,
        )


class ValidationError(PlatformException):
    """Raised when a model fails schema or business validation."""

    def __init__(self, detail: str, context: Optional[Dict[str, Any]] = None):
        super().__init__(
            detail=detail,
            error_code="VALIDATION_ERROR",
            status_code=400,
            context=context,
        )


class NormalizationError(PlatformException):
    """Raised when aligning or normalizing datasets fails."""

    def __init__(self, detail: str, context: Optional[Dict[str, Any]] = None):
        super().__init__(
            detail=detail,
            error_code="NORMALIZATION_ERROR",
            status_code=422,
            context=context,
        )


class SerializationError(PlatformException):
    """Raised when serializing or deserializing JSON artifacts fails."""

    def __init__(self, detail: str, context: Optional[Dict[str, Any]] = None):
        super().__init__(
            detail=detail,
            error_code="SERIALIZATION_ERROR",
            status_code=500,
            context=context,
        )


class ReportGenerationError(PlatformException):
    """Raised when synthesizing or compiling reports fails."""

    def __init__(self, detail: str, context: Optional[Dict[str, Any]] = None):
        super().__init__(
            detail=detail,
            error_code="REPORT_GENERATION_ERROR",
            status_code=500,
            context=context,
        )


class IntegrationError(PlatformException):
    """Raised when communicating with an external platform/tool fails."""

    def __init__(self, detail: str, context: Optional[Dict[str, Any]] = None):
        super().__init__(
            detail=detail,
            error_code="INTEGRATION_ERROR",
            status_code=502,
            context=context,
        )


class ResourceNotFoundError(PlatformException):
    """Raised when a requested run, report, test, or file does not exist."""

    def __init__(self, detail: str, context: Optional[Dict[str, Any]] = None):
        super().__init__(
            detail=detail,
            error_code="NOT_FOUND",
            status_code=404,
            context=context,
        )
