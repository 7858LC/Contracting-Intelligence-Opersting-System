"""CIOS FastAPI application entry point."""

import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse

from cios.api.v1.router import api_router
from cios.config import settings
from cios.core.database import engine
from cios.core.redis import redis_client
from cios.core.telemetry import setup_telemetry

log = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    log.info("CIOS API starting", env=settings.app_env, version="1.0.0")
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

    @app.middleware("http")
    async def request_timing(request: Request, call_next: any) -> Response:
        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception as exc:
            # An unhandled (non-HTTPException) error raised in a route — e.g.
            # a raw Qdrant/S3 client exception — can't be caught with a plain
            # @app.exception_handler(Exception): Starlette's BaseHTTPMiddleware
            # (what `@app.middleware("http")` is, i.e. this function) always
            # re-raises the exception it captured from call_next()'s inner
            # task, even when an app-level handler already built and sent a
            # real response for it (see starlette/middleware/base.py's
            # call_next, `raise app_exc from ...`). Left uncaught here, that
            # re-raised exception would propagate to the outer, framework-
            # level ServerErrorMiddleware, whose generic 500 never passes
            # back through CORSMiddleware's header-adding logic — a browser
            # then reports "blocked by CORS policy" instead of the real 500.
            # This is exactly what made cios/vector/tenant_store.py's
            # search() bug (and at least one S3-misconfiguration report) look
            # like a CORS issue rather than the backend error either actually
            # was. Catching here, with CORSMiddleware registered *after* (so
            # it wraps) this middleware below, keeps every response —
            # including this fallback one — flowing through CORS. Detail is
            # intentionally generic; the real exception is logged, not
            # exposed to the client.
            log.error(
                "unhandled_exception",
                path=request.url.path,
                method=request.method,
                exc_info=exc,
            )
            response = JSONResponse(status_code=500, content={"detail": "Internal server error"})
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

    # Registered after request_timing above so CORS ends up as the outermost
    # user middleware (Starlette wraps in reverse registration order) —
    # required for the fallback 500 built inside request_timing's except
    # block to actually carry CORS headers; see that function's comment.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

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
