"""Dépendances de sécurité et d'authentification pour les routes FastAPI."""

from __future__ import annotations

import hmac
from typing import Annotated

from fastapi import Header, HTTPException

from app.core.config import settings


async def require_internal_api_key(
    api_key: Annotated[str | None, Header(alias="X-Internal-Api-Key")] = None,
) -> None:
    """Vérifie que la requête provient bien du backend interne Node.js."""
    expected = settings.internal_api_key.get_secret_value()
    if api_key is None or not hmac.compare_digest(api_key, expected):
        raise HTTPException(status_code=401, detail="Invalid internal API key")


async def get_user_id(
    user_id: Annotated[str | None, Header(alias="X-User-Id")] = None,
) -> str:
    """Extrait et valide l'identifiant utilisateur fourni par le backend Node.js."""
    if not user_id or not user_id.strip():
        raise HTTPException(
            status_code=400,
            detail="Header 'X-User-Id' requis pour garantir l'isolation des données.",
        )
    return user_id.strip()
