"""Client d'embeddings singleton via Ollama.

Fournit un point d'accès unique au modèle d'embeddings configuré,
avec batching automatique et retry sur erreurs réseau.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence

from langchain_ollama import OllamaEmbeddings
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.core.config import settings
from app.core.exceptions import VectorStoreError

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------
# Singleton
# --------------------------------------------------------------------------
_embeddings: OllamaEmbeddings | None = None


def _get_embeddings() -> OllamaEmbeddings:
    """Retourne l'instance singleton de OllamaEmbeddings."""
    global _embeddings
    if _embeddings is None:
        _embeddings = OllamaEmbeddings(
            model=settings.embedding_model,
            base_url=settings.ollama_base_url,
        )
        logger.info(
            "Client embeddings initialisé (modèle=%s, url=%s)",
            settings.embedding_model,
            settings.ollama_base_url,
        )
    return _embeddings


# --------------------------------------------------------------------------
# Retry — on retente sur les erreurs réseau (httpx, connexion)
# --------------------------------------------------------------------------
_RETRY = retry(
    retry=retry_if_exception_type((ConnectionError, OSError, TimeoutError)),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    reraise=True,
)


@_RETRY
def _embed_single_batch(texts: list[str]) -> list[list[float]]:
    """Embed un seul lot de textes (sans batching interne)."""
    return _get_embeddings().embed_documents(texts)


# --------------------------------------------------------------------------
# API publique
# --------------------------------------------------------------------------
def embed_texts(texts: Sequence[str]) -> list[list[float]]:
    """Génère les embeddings pour une liste de textes, par lots.

    Les textes sont traités par lots de ``settings.embed_batch_size``
    pour éviter de saturer la mémoire ou le timeout Ollama.

    Args:
        texts: Textes à encoder.

    Returns:
        Liste de vecteurs, un par texte, dans le même ordre.

    Raises:
        VectorStoreError: Si Ollama est injoignable après retries.
    """
    if not texts:
        return []

    batch_size = settings.embed_batch_size
    all_embeddings: list[list[float]] = []

    try:
        for start in range(0, len(texts), batch_size):
            batch = list(texts[start : start + batch_size])
            batch_embeddings = _embed_single_batch(batch)
            all_embeddings.extend(batch_embeddings)
            if start + batch_size < len(texts):
                logger.debug(
                    "Embeddings : lot %d–%d / %d",
                    start,
                    start + len(batch),
                    len(texts),
                )
    except Exception as exc:
        logger.error("Échec de génération des embeddings : %s", exc)
        raise VectorStoreError(
            "Impossible de générer les embeddings. "
            "Vérifiez qu'Ollama est démarré et que le modèle "
            f"« {settings.embedding_model} » est disponible."
        ) from exc

    return all_embeddings


def embed_query(text: str) -> list[float]:
    """Génère l'embedding d'une seule requête (question utilisateur).

    Raises:
        VectorStoreError: Si Ollama est injoignable.
    """
    try:
        return _get_embeddings().embed_query(text)
    except Exception as exc:
        logger.error("Échec d'embedding de la requête : %s", exc)
        raise VectorStoreError(
            "Impossible de générer l'embedding de la requête. "
            "Vérifiez qu'Ollama est démarré."
        ) from exc
