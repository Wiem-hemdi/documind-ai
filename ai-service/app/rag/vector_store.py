"""Gestion centralisée de la collection Qdrant.

Client singleton, création de collection et d'index, upsert, recherche,
suppression — avec filtre ``user_id`` obligatoire sur chaque opération.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from uuid import NAMESPACE_URL, uuid5

from qdrant_client import QdrantClient, models
from qdrant_client.http.exceptions import ApiException, UnexpectedResponse
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
# Dataclasses de résultat
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class ScoredChunk:
    """Chunk retourné par une recherche Qdrant avec son score de similarité."""

    text: str
    page: int | None
    location: str | None
    filename: str
    document_id: str
    chunk_index: int
    score: float


@dataclass(frozen=True)
class ChunkPayload:
    """Payload complet d'un chunk stocké dans Qdrant."""

    text: str
    page: int | None
    location: str | None
    filename: str
    document_id: str
    user_id: str
    chunk_index: int


# --------------------------------------------------------------------------
# Client singleton
# --------------------------------------------------------------------------
_client: QdrantClient | None = None


def _get_client() -> QdrantClient:
    """Retourne le client Qdrant singleton."""
    global _client
    if _client is None:
        api_key = (
            settings.qdrant_api_key.get_secret_value()
            if settings.qdrant_api_key
            else None
        )
        _client = QdrantClient(url=settings.qdrant_url, api_key=api_key)
        logger.info("Client Qdrant connecté à %s", settings.qdrant_url)
    return _client


def close_client() -> None:
    """Ferme proprement le client Qdrant (à appeler au shutdown)."""
    global _client
    if _client is not None:
        _client.close()
        _client = None
        logger.info("Client Qdrant fermé")


# --------------------------------------------------------------------------
# Création de collection et index
# --------------------------------------------------------------------------
_RETRY = retry(
    retry=retry_if_exception_type((ConnectionError, OSError, TimeoutError)),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    reraise=True,
)


@_RETRY
def ensure_collection() -> None:
    """Crée la collection et les index payload si nécessaire.

    Idempotent : ne fait rien si la collection existe déjà.
    """
    client = _get_client()
    collection = settings.qdrant_collection

    try:
        if client.collection_exists(collection):
            logger.info("Collection « %s » déjà existante", collection)
            _ensure_payload_indexes(client, collection)
            return

        client.create_collection(
            collection_name=collection,
            vectors_config=models.VectorParams(
                size=settings.embedding_dimension,
                distance=models.Distance.COSINE,
            ),
        )
        logger.info(
            "Collection « %s » créée (dim=%d, cosine)",
            collection,
            settings.embedding_dimension,
        )
        _ensure_payload_indexes(client, collection)

    except (ApiException, UnexpectedResponse) as exc:
        logger.error("Échec de création de la collection : %s", exc)
        raise VectorStoreError(
            "Impossible d'initialiser la base vectorielle Qdrant."
        ) from exc


def _ensure_payload_indexes(client: QdrantClient, collection: str) -> None:
    """Crée les index keyword sur user_id et document_id si manquants."""
    for field in ("user_id", "document_id"):
        try:
            client.create_payload_index(
                collection_name=collection,
                field_name=field,
                field_schema=models.PayloadSchemaType.KEYWORD,
                wait=True,
            )
        except (ApiException, UnexpectedResponse):
            # L'index existe probablement déjà — Qdrant renvoie 400
            pass


# --------------------------------------------------------------------------
# ID déterministe des points
# --------------------------------------------------------------------------
def _point_id(user_id: str, document_id: str, chunk_index: int) -> str:
    """Génère un UUID déterministe pour un chunk."""
    return str(uuid5(NAMESPACE_URL, f"{user_id}:{document_id}:{chunk_index}"))


# --------------------------------------------------------------------------
# Filtres
# --------------------------------------------------------------------------
def _user_filter(user_id: str) -> models.Filter:
    """Filtre sur user_id uniquement."""
    return models.Filter(
        must=[
            models.FieldCondition(
                key="user_id",
                match=models.MatchValue(value=user_id),
            ),
        ]
    )


def _document_filter(user_id: str, document_id: str) -> models.Filter:
    """Filtre sur user_id + document_id."""
    return models.Filter(
        must=[
            models.FieldCondition(
                key="user_id",
                match=models.MatchValue(value=user_id),
            ),
            models.FieldCondition(
                key="document_id",
                match=models.MatchValue(value=document_id),
            ),
        ]
    )


# --------------------------------------------------------------------------
# Opérations CRUD
# --------------------------------------------------------------------------
def count_document(user_id: str, document_id: str) -> int:
    """Retourne le nombre de chunks indexés pour un document."""
    try:
        result = _get_client().count(
            collection_name=settings.qdrant_collection,
            count_filter=_document_filter(user_id, document_id),
            exact=True,
        )
        return result.count
    except (ApiException, UnexpectedResponse) as exc:
        logger.error("Échec du comptage de chunks : %s", exc)
        raise VectorStoreError("Erreur lors de l'accès à Qdrant.") from exc


def upsert_chunks(
    user_id: str,
    document_id: str,
    filename: str,
    chunks_data: list[dict],
    embeddings: list[list[float]],
) -> None:
    """Upsert des chunks dans Qdrant par lots de 100.

    Args:
        user_id: Identifiant de l'utilisateur.
        document_id: Identifiant du document.
        filename: Nom du fichier original.
        chunks_data: Liste de dicts avec ``text``, ``page``, ``location``,
                     ``chunk_index``.
        embeddings: Vecteurs correspondants (même ordre).
    """
    client = _get_client()
    collection = settings.qdrant_collection
    batch_size = 100

    try:
        for start in range(0, len(chunks_data), batch_size):
            end = min(start + batch_size, len(chunks_data))
            points = []
            for i in range(start, end):
                chunk = chunks_data[i]
                points.append(
                    models.PointStruct(
                        id=_point_id(user_id, document_id, chunk["chunk_index"]),
                        vector=embeddings[i],
                        payload={
                            "user_id": user_id,
                            "document_id": document_id,
                            "filename": filename,
                            "page": chunk.get("page"),
                            "location": chunk.get("location"),
                            "chunk_index": chunk["chunk_index"],
                            "text": chunk["text"],
                        },
                    )
                )
            client.upsert(
                collection_name=collection,
                points=points,
                wait=True,
            )
            logger.debug("Upsert lots %d–%d / %d", start, end, len(chunks_data))

    except (ApiException, UnexpectedResponse) as exc:
        logger.error("Échec de l'upsert dans Qdrant : %s", exc)
        raise VectorStoreError(
            "Impossible d'indexer les chunks dans Qdrant."
        ) from exc


def delete_document(user_id: str, document_id: str) -> None:
    """Supprime tous les chunks d'un document pour un utilisateur."""
    client = _get_client()
    collection = settings.qdrant_collection

    try:
        if not client.collection_exists(collection):
            return
        client.delete(
            collection_name=collection,
            points_selector=models.FilterSelector(
                filter=_document_filter(user_id, document_id)
            ),
            wait=True,
        )
        logger.info(
            "Index supprimé pour document=%s, user=%s", document_id, user_id
        )
    except (ApiException, UnexpectedResponse) as exc:
        logger.error("Échec de suppression de l'index : %s", exc)
        raise VectorStoreError(
            "La suppression de l'index documentaire a échoué."
        ) from exc


def search(
    embedding: list[float],
    user_id: str,
    top_k: int | None = None,
    document_ids: list[str] | None = None,
) -> list[ScoredChunk]:
    """Recherche les chunks les plus proches, filtrés par user_id.

    Args:
        embedding: Vecteur de la requête.
        user_id: Identifiant de l'utilisateur (filtre obligatoire).
        top_k: Nombre de résultats (défaut : ``settings.retrieval_top_k``).
        document_ids: Si fourni, limite la recherche à ces documents.

    Returns:
        Liste de :class:`ScoredChunk` ordonnés par score décroissant.
    """
    client = _get_client()
    k = top_k or settings.retrieval_top_k

    # Construction du filtre
    conditions: list[models.Condition] = [
        models.FieldCondition(
            key="user_id",
            match=models.MatchValue(value=user_id),
        ),
    ]
    if document_ids:
        conditions.append(
            models.FieldCondition(
                key="document_id",
                match=models.MatchAny(any=document_ids),
            ),
        )

    query_filter = models.Filter(must=conditions)

    try:
        results = client.query_points(
            collection_name=settings.qdrant_collection,
            query=embedding,
            query_filter=query_filter,
            limit=k,
            with_payload=True,
        ).points
    except (ApiException, UnexpectedResponse) as exc:
        logger.error("Échec de la recherche Qdrant : %s", exc)
        raise VectorStoreError(
            "La recherche documentaire est indisponible."
        ) from exc

    scored: list[ScoredChunk] = []
    for point in results:
        payload = point.payload or {}
        scored.append(
            ScoredChunk(
                text=payload.get("text", ""),
                page=payload.get("page"),
                location=payload.get("location"),
                filename=payload.get("filename", ""),
                document_id=payload.get("document_id", ""),
                chunk_index=payload.get("chunk_index", 0),
                score=point.score,
            )
        )
    return scored


def get_document_chunks(user_id: str, document_id: str) -> list[ChunkPayload]:
    """Récupère tous les chunks d'un document, ordonnés par chunk_index.

    Utilisé pour le résumé, l'extraction et l'explication.
    """
    client = _get_client()
    collection = settings.qdrant_collection
    doc_filter = _document_filter(user_id, document_id)

    try:
        if not client.collection_exists(collection):
            return []

        all_points = []
        offset = None
        while True:
            result = client.scroll(
                collection_name=collection,
                scroll_filter=doc_filter,
                limit=100,
                offset=offset,
                with_payload=True,
                with_vectors=False,
            )
            points, next_offset = result
            all_points.extend(points)
            if next_offset is None:
                break
            offset = next_offset

    except (ApiException, UnexpectedResponse) as exc:
        logger.error("Échec de récupération des chunks : %s", exc)
        raise VectorStoreError(
            "Impossible de récupérer les chunks du document."
        ) from exc

    chunks = []
    for point in all_points:
        payload = point.payload or {}
        chunks.append(
            ChunkPayload(
                text=payload.get("text", ""),
                page=payload.get("page"),
                location=payload.get("location"),
                filename=payload.get("filename", ""),
                document_id=payload.get("document_id", ""),
                user_id=payload.get("user_id", ""),
                chunk_index=payload.get("chunk_index", 0),
            )
        )

    # Trier par chunk_index
    chunks.sort(key=lambda c: c.chunk_index)
    return chunks


def list_user_documents(user_id: str) -> list[dict]:
    """Liste les documents distincts d'un utilisateur.

    Retourne une liste de dicts ``{document_id, filename, chunk_count}``.
    """
    client = _get_client()
    collection = settings.qdrant_collection
    user_f = _user_filter(user_id)

    try:
        if not client.collection_exists(collection):
            return []

        # Scroll tous les points de l'utilisateur (payload partiel)
        documents: dict[str, dict] = {}
        offset = None
        while True:
            result = client.scroll(
                collection_name=collection,
                scroll_filter=user_f,
                limit=100,
                offset=offset,
                with_payload=["document_id", "filename"],
                with_vectors=False,
            )
            points, next_offset = result
            for point in points:
                payload = point.payload or {}
                doc_id = payload.get("document_id", "")
                if doc_id not in documents:
                    documents[doc_id] = {
                        "document_id": doc_id,
                        "filename": payload.get("filename", ""),
                        "chunk_count": 0,
                    }
                documents[doc_id]["chunk_count"] += 1
            if next_offset is None:
                break
            offset = next_offset

    except (ApiException, UnexpectedResponse) as exc:
        logger.error("Échec de listage des documents : %s", exc)
        raise VectorStoreError(
            "Impossible de lister les documents."
        ) from exc

    return list(documents.values())
