import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.routes import documents, health
from app.core.config import settings
from app.core.exceptions import AppError
from app.core.logging import setup_logging

setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Démarrage de %s (env=%s)", settings.app_name, settings.app_env)
    yield
    logger.info("Arrêt de %s", settings.app_name)


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        lifespan=lifespan,
        docs_url=None if settings.is_production else "/docs",
        redoc_url=None,
    )

    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        request_id = request.headers.get("x-request-id") or uuid.uuid4().hex[:12]
        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            logger.exception("[%s] %s %s : exception non gérée",
                             request_id, request.method, request.url.path)
            raise
        duration_ms = (time.perf_counter() - start) * 1000
        logger.info("[%s] %s %s -> %s (%.0f ms)", request_id, request.method,
                    request.url.path, response.status_code, duration_ms)
        response.headers["x-request-id"] = request_id
        return response

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError):
        logger.warning("%s : %s", exc.code, exc.message)
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.code, "message": exc.message}},
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception):
        return JSONResponse(
            status_code=500,
            content={"error": {"code": "internal_error",
                               "message": "Erreur interne du service."}},
        )

    app.include_router(health.router)
    app.include_router(documents.router)
    return app


app = create_app()