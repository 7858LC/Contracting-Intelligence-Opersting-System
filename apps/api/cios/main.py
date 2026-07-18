"""CIOS FastAPI application entry point."""
import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse

from cios.config import settings
from cios.core.database import engine, init_db
from cios.core.redis import redis_client
from cios.core.telemetry import setup_telemetry
from cios.api.v1.router import api_router

log = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    log.info("CIOS API starting", env=settings.app_env, version="1.0.0")
    await init_db()
    await redis_client.ping()
    log.info("CIOS API ready")
    yield
    log.info("CIOS API shutting down")
    await engine.dispose()
    await redis_client.aclose()


def create_app() -> FastAPI:
    setup_telemetry()

    app = FastAPI(
        title="CIOS API",
        description="Contract Intelligence Operating System — Procurement Intelligence Platform",
        version="1.0.0",
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
        lifespan=lifespan,
    )

    app.add_middleware(GZipMiddleware, minimum_size=1000)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def request_timing(request: Request, call_next: any) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000
        response.headers["X-Response-Time"] = f"{duration_ms:.1f}ms"
        log.info(
            "http_request",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            duration_ms=round(duration_ms, 1),
        )
        return response

    @app.get("/health", tags=["System"])
    async def health() -> dict:
        return {"status": "healthy", "version": "1.0.0", "env": settings.app_env}

    @app.get("/health/ready", tags=["System"])
    async def readiness() -> dict:
        try:
            await redis_client.ping()
            return {"status": "ready", "dependencies": {"redis": "ok"}}
        except Exception as e:
            return JSONResponse(status_code=503, content={"status": "not_ready", "error": str(e)})

    app.include_router(api_router, prefix="/api/v1")

    return app


app = create_app()
