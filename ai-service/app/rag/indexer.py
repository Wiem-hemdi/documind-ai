"""Pipeline d'indexation complète d'un document.

Orchestre : load_sections → split_sections → embed_texts → upsert_chunks.
L'indexation est idempotente : si le nombre de chunks n'a pas changé,
le document n'est pas réindexé.
"""

from __future__ import annotations

import logging
import tempfile
from dataclasses import dataclass
from pathlib import Path

from app.core.exceptions import DocumentProcessingError
from app.document_processing.loaders import load_sections
from app.document_processing.splitter import Chunk, split_sections
from app.embeddings.embedding_service import embed_texts
from app.rag.vector_store import count_document, delete_document, upsert_chunks

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class IndexResult:
    """Résultat de l'indexation d'un document.

    Attributes:
        chunk_count: Nombre total de chunks indexés.
        was_reindexed: ``True`` si le document a été (ré)indexé,
                       ``False`` s'il était déjà à jour.
    """

    chunk_count: int
    was_reindexed: bool


def index_document(
    file_content: bytes,
    filename: str,
    user_id: str,
    document_id: str,
) -> IndexResult:
    """Indexe un document dans Qdrant.

    Pipeline complet :

    1. Sauvegarde temporaire du fichier.
    2. Extraction des sections via les loaders.
    3. Nettoyage + découpage en chunks.
    4. Vérification d'idempotence (nombre de chunks existants).
    5. Génération des embeddings par lots.
    6. Upsert dans Qdrant.

    Args:
        file_content: Contenu brut du fichier.
        filename: Nom original du fichier (avec extension).
        user_id: Identifiant de l'utilisateur propriétaire.
        document_id: Identifiant unique du document.

    Returns:
        :class:`IndexResult` avec le nombre de chunks et le statut.

    Raises:
        DocumentProcessingError: Si le fichier est illisible ou vide.
        VectorStoreError: Si Qdrant ou Ollama sont indisponibles.
    """
    # 1. Sauvegarde temporaire
    suffix = Path(filename).suffix.lower()
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir) / f"document{suffix}"
        tmp_path.write_bytes(file_content)

        # 2. Extraction
        sections = load_sections(tmp_path)

        # 3. Nettoyage + découpage
        chunks: list[Chunk] = split_sections(sections)

    if not chunks:
        raise DocumentProcessingError(
            "Aucun texte exploitable n'a été trouvé dans le document."
        )

    logger.info(
        "Document %s (%s) : %d chunks à indexer",
        document_id,
        filename,
        len(chunks),
    )

    # 4. Idempotence : vérifier si déjà indexé avec le même nombre de chunks
    existing_count = count_document(user_id, document_id)
    if existing_count == len(chunks):
        logger.info(
            "Document %s déjà indexé avec %d chunks, skip",
            document_id,
            existing_count,
        )
        return IndexResult(chunk_count=len(chunks), was_reindexed=False)

    # Si le nombre diffère, on supprime l'ancien index
    if existing_count > 0:
        logger.info(
            "Document %s : %d chunks existants ≠ %d nouveaux, réindexation",
            document_id,
            existing_count,
            len(chunks),
        )
        delete_document(user_id, document_id)

    # 5. Génération des embeddings par lots
    texts = [chunk.text for chunk in chunks]
    embeddings = embed_texts(texts)

    # 6. Upsert dans Qdrant
    chunks_data = [
        {
            "text": chunk.text,
            "page": chunk.page,
            "location": chunk.location,
            "chunk_index": chunk.chunk_index,
        }
        for chunk in chunks
    ]
    upsert_chunks(user_id, document_id, filename, chunks_data, embeddings)

    logger.info(
        "Document %s indexé avec succès : %d chunks", document_id, len(chunks)
    )
    return IndexResult(chunk_count=len(chunks), was_reindexed=True)
