"""Découpage des sections extraites en chunks indexables.

Chaque chunk conserve les métadonnées de sa section source
(page, location) et reçoit un ``chunk_index`` séquentiel global.
Le texte est nettoyé via :func:`~app.document_processing.cleaner.clean_text`
avant le découpage.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from dataclasses import dataclass

from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.core.config import settings
from app.document_processing.cleaner import clean_text
from app.document_processing.models import ExtractedSection

logger = logging.getLogger(__name__)

# Séparateurs adaptés au français, anglais, arabe :
# double saut de ligne, simple saut, fin de phrase, espace, vide.
_SEPARATORS = ["\n\n", "\n", ". ", " ", ""]


@dataclass(frozen=True)
class Chunk:
    """Un morceau de texte prêt à être indexé dans Qdrant.

    Attributes:
        text: Texte nettoyé du chunk.
        page: Numéro de page (PDF) ou de diapositive (PPTX), sinon None.
        location: Repère lisible pour les sources.
        chunk_index: Index séquentiel du chunk dans le document (0-based).
    """

    text: str
    page: int | None = None
    location: str | None = None
    chunk_index: int = 0


def split_sections(sections: Iterator[ExtractedSection]) -> list[Chunk]:
    """Découpe un flux de sections en chunks avec métadonnées.

    1. Nettoie chaque section via :func:`clean_text`.
    2. Découpe via ``RecursiveCharacterTextSplitter``.
    3. Propage ``page`` et ``location`` de la section source.
    4. Attribue un ``chunk_index`` séquentiel global (0-based).

    Args:
        sections: Itérateur de sections extraites d'un document.

    Returns:
        Liste ordonnée de :class:`Chunk`.
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        separators=_SEPARATORS,
        strip_whitespace=True,
    )

    chunks: list[Chunk] = []
    global_index = 0

    for section in sections:
        cleaned = clean_text(section.text)
        if not cleaned:
            continue

        # split_text retourne une liste de strings
        parts = splitter.split_text(cleaned)

        for part in parts:
            if not part.strip():
                continue
            chunks.append(
                Chunk(
                    text=part,
                    page=section.page,
                    location=section.location,
                    chunk_index=global_index,
                )
            )
            global_index += 1

    logger.info("Découpage terminé : %d chunks produits", len(chunks))
    return chunks
