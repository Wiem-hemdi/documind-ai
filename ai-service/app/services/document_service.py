"""Service métier de gestion des documents.

Orchestre l'upload, l'indexation, la suppression et le listage
des documents d'un utilisateur.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from app.rag.indexer import IndexResult, index_document
from app.rag.vector_store import (
    delete_document as vs_delete_document,
    list_user_documents,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DocumentInfo:
    """Informations sur un document indexé."""

    document_id: str
    filename: str
    chunk_count: int


def upload_and_index(
    file_content: bytes,
    filename: str,
    user_id: str,
    document_id: str,
) -> IndexResult:
    """Upload et indexe un document.

    Args:
        file_content: Contenu brut du fichier.
        filename: Nom original du fichier.
        user_id: Identifiant de l'utilisateur.
        document_id: Identifiant unique du document.

    Returns:
        :class:`IndexResult` avec le nombre de chunks et le statut.
    """
    logger.info(
        "Indexation demandée : document=%s, fichier=%s, user=%s",
        document_id,
        filename,
        user_id,
    )
    return index_document(file_content, filename, user_id, document_id)


def delete(user_id: str, document_id: str) -> None:
    """Supprime l'index d'un document."""
    logger.info("Suppression demandée : document=%s, user=%s", document_id, user_id)
    vs_delete_document(user_id, document_id)


def list_documents(user_id: str) -> list[DocumentInfo]:
    """Liste les documents indexés d'un utilisateur."""
    raw = list_user_documents(user_id)
    return [
        DocumentInfo(
            document_id=doc["document_id"],
            filename=doc["filename"],
            chunk_count=doc["chunk_count"],
        )
        for doc in raw
    ]
