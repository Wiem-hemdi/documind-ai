import logging

import httpx
from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict:
    """Liveness : utilisé par le healthcheck Docker. Ne dépend d'aucun service externe."""
    return {"status": "ok", "service": settings.app_name}


async def _check_qdrant(client: httpx.AsyncClient) -> dict:
    headers = {}
    if settings.qdrant_api_key:
        headers["api-key"] = settings.qdrant_api_key.get_secret_value()
    try:
        response = await client.get(f"{settings.qdrant_url}/readyz", headers=headers)
        return {"ok": response.status_code == 200}
    except httpx.HTTPError as exc:
        logger.warning("Qdrant injoignable : %s", exc)
        return {"ok": False, "error": "injoignable"}


async def _check_ollama(client: httpx.AsyncClient) -> dict:
    try:
        response = await client.get(f"{settings.ollama_base_url}/api/tags")
        response.raise_for_status()
        names = {m["name"] for m in response.json().get("models", [])}
    except (httpx.HTTPError, ValueError, KeyError) as exc:
        logger.warning("Ollama injoignable : %s", exc)
        return {"ok": False, "error": "injoignable"}

    def has(model: str) -> bool:
        return model in names or f"{model}:latest" in names

    llm_ok = has(settings.llm_model)
    embedding_ok = has(settings.embedding_model)
    return {
        "ok": llm_ok and embedding_ok,
        "llm_model_present": llm_ok,
        "embedding_model_present": embedding_ok,
    }


@router.get("/health/ready")
async def ready() -> JSONResponse:
    """Readiness : vérifie que Qdrant et Ollama sont prêts."""
    async with httpx.AsyncClient(timeout=3.0) as client:
        qdrant = await _check_qdrant(client)
        ollama = await _check_ollama(client)

    is_ready = qdrant["ok"] and ollama["ok"]
    return JSONResponse(
        status_code=200 if is_ready else 503,
        content={
            "status": "ready" if is_ready else "not_ready",
            "qdrant": qdrant,
            "ollama": ollama,
        },
    )