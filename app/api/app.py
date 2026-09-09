"""
app.py — Production-grade FastAPI Application Factory for PerfPilot.
Provides OpenAPI documentation (/docs), modular routers, and static file mounting.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError as PydanticValidationError

from app.core.constants import WEB_DIR, RESULTS_DIR
from app.core.exceptions import PlatformException
from app.api.middleware.error_handler import (
    platform_exception_handler,
    pydantic_validation_exception_handler,
    generic_exception_handler,
)

# Route modules
from app.api.routes.status import router as status_router
from app.api.routes.tests import router as tests_router
from app.api.routes.execution import router as execution_router
from app.api.routes.ingestion import router as ingestion_router
from app.api.routes.runs import router as runs_router
from app.api.routes.compare import router as compare_router
from app.api.routes.trends import router as trends_router
from app.api.routes.ai_studio import router as ai_studio_router
from app.api.routes.reports import router as reports_router


def create_app() -> FastAPI:
    """Creates and configures the FastAPI platform instance."""
    app = FastAPI(
        title="PerfPilot Performance Engineering Platform",
        description="Unified load testing platform supporting JMeter, BlazeMeter, and NeoLoad with decoupled execution, typed domain contracts, and autonomous intelligence.",
        version="2.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # 1. CORS Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 2. Centralized Exception Handlers
    app.add_exception_handler(PlatformException, platform_exception_handler)
    app.add_exception_handler(PydanticValidationError, pydantic_validation_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)

    # 3. Register Modular Routers
    app.include_router(status_router)
    app.include_router(tests_router)
    app.include_router(execution_router)
    app.include_router(ingestion_router)
    app.include_router(runs_router)
    app.include_router(compare_router)
    app.include_router(trends_router)
    app.include_router(ai_studio_router)
    app.include_router(reports_router)

    # 4. Mount Static Results Directory (/Results/*)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    app.mount("/Results", StaticFiles(directory=str(RESULTS_DIR)), name="results")

    # 5. Mount Static Frontend Single Page App (/)
    WEB_DIR.mkdir(parents=True, exist_ok=True)
    app.mount("/", StaticFiles(directory=str(WEB_DIR), html=True), name="web")

    return app


app = create_app()
