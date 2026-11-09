"""Fonctions avancées RAG : résumé, extraction, comparaison, explication.

- Résumé : Map-Reduce sur les chunks d'un document.
- Extraction : extraction structurée d'informations clés.
- Comparaison : rassemblement des chunks par document_id puis analyse comparative.
- Explication : explication pédagogique d'un passage ciblé.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from app.core.exceptions import DocumentProcessingError, NotFoundError
from app.rag.chains import (
    compare_documents as chain_compare,
    explain_passage as chain_explain,
    extract_key_info as chain_extract,
    summarize_map,
    summarize_reduce,
)
from app.rag.vector_store import ChunkPayload, get_document_chunks

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SummaryResult:
    """Résultat d'un résumé de document."""

    document_id: str
    filename: str
    summary: str
    chunk_count: int


@dataclass(frozen=True)
class ExtractionResult:
    """Résultat d'une extraction d'informations clés."""

    document_id: str
    filename: str
    extracted_info: str


@dataclass(frozen=True)
class ComparisonResult:
    """Résultat de la comparaison de plusieurs documents."""

    document_ids: list[str]
    comparison: str


@dataclass(frozen=True)
class ExplanationResult:
    """Résultat de l'explication d'un passage précis."""

    document_id: str
    explanation: str
    passage: str


def summarize_document(user_id: str, document_id: str) -> SummaryResult:
    """Génère un résumé complet d'un document par map-reduce.

    1. Récupère tous les chunks ordonnés du document.
    2. Phase Map : résume chaque chunk ou groupe de chunks.
    3. Phase Reduce : consolide en un résumé structuré final.
    """
    chunks: list[ChunkPayload] = get_document_chunks(user_id, document_id)
    if not chunks:
        raise NotFoundError("Document introuvable ou vide pour cet utilisateur.")

    filename = chunks[0].filename

    # Si peu de chunks (<= 3), on peut résumer directement
    if len(chunks) <= 3:
        combined = "\n\n".join(c.text for c in chunks)
        final_summary = summarize_map(combined)
    else:
        # Phase Map : résumer par lot de 2 chunks pour réduire la taille
        partial_summaries: list[str] = []
        batch_size = 2
        for i in range(0, len(chunks), batch_size):
            group_text = "\n\n".join(c.text for c in chunks[i : i + batch_size])
            partial_summaries.append(summarize_map(group_text))

        # Phase Reduce
        final_summary = summarize_reduce(partial_summaries)

    return SummaryResult(
        document_id=document_id,
        filename=filename,
        summary=final_summary,
        chunk_count=len(chunks),
    )


def extract_document_info(user_id: str, document_id: str) -> ExtractionResult:
    """Extrait les informations importantes d'un document."""
    chunks = get_document_chunks(user_id, document_id)
    if not chunks:
        raise NotFoundError("Document introuvable ou vide pour cet utilisateur.")

    filename = chunks[0].filename
    # Prendre les chunks représentatifs (début, milieu, fin si volumineux)
    if len(chunks) <= 10:
        full_text = "\n\n".join(c.text for c in chunks)
    else:
        selected_chunks = chunks[:4] + chunks[len(chunks)//2 - 1 : len(chunks)//2 + 1] + chunks[-4:]
        full_text = "\n\n".join(c.text for c in selected_chunks)

    extracted = chain_extract(full_text)
    return ExtractionResult(
        document_id=document_id,
        filename=filename,
        extracted_info=extracted,
    )


def compare_user_documents(
    user_id: str,
    document_ids: list[str],
    question: str = "",
) -> ComparisonResult:
    """Compare plusieurs documents appartenant à l'utilisateur."""
    if len(document_ids) < 2:
        raise DocumentProcessingError("Veuillez sélectionner au moins 2 documents à comparer.")

    docs_payload: list[str] = []
    for doc_id in document_ids:
        chunks = get_document_chunks(user_id, doc_id)
        if not chunks:
            raise NotFoundError(f"Document '{doc_id}' introuvable pour cet utilisateur.")
        fname = chunks[0].filename
        # Extraire les 5 premiers chunks comme résumé représentatif
        content_sample = "\n".join(c.text for c in chunks[:5])
        docs_payload.append(f"--- Document: {fname} (ID: {doc_id}) ---\n{content_sample}")

    combined_docs = "\n\n".join(docs_payload)
    comparison = chain_compare(combined_docs, question=question)

    return ComparisonResult(
        document_ids=document_ids,
        comparison=comparison,
    )


def explain_document_passage(
    user_id: str,
    document_id: str,
    page: int | None = None,
    chunk_index: int | None = None,
    passage_text: str | None = None,
) -> ExplanationResult:
    """Explique un passage ciblé d'un document."""
    chunks = get_document_chunks(user_id, document_id)
    if not chunks:
        raise NotFoundError("Document introuvable pour cet utilisateur.")

    target_passage = ""
    surrounding_context = ""

    if chunk_index is not None:
        matched = next((c for c in chunks if c.chunk_index == chunk_index), None)
        if not matched:
            raise NotFoundError(f"Chunk d'index {chunk_index} introuvable.")
        target_passage = matched.text
        # Contexte précédent et suivant
        prev_chunk = next((c for c in chunks if c.chunk_index == chunk_index - 1), None)
        next_chunk = next((c for c in chunks if c.chunk_index == chunk_index + 1), None)
        ctx = []
        if prev_chunk:
            ctx.append(f"[Précédent]: {prev_chunk.text}")
        if next_chunk:
            ctx.append(f"[Suivant]: {next_chunk.text}")
        surrounding_context = "\n\n".join(ctx)

    elif page is not None:
        page_chunks = [c for c in chunks if c.page == page]
        if not page_chunks:
            raise NotFoundError(f"Aucun contenu trouvé pour la page {page}.")
        target_passage = "\n\n".join(c.text for c in page_chunks)

    elif passage_text:
        target_passage = passage_text.strip()
        # Recherche d'un chunk contenant le texte ou similaire
        matching = [c for c in chunks if passage_text.lower() in c.text.lower()]
        if matching:
            surrounding_context = f"Trouvé dans le chunk {matching[0].chunk_index} (page {matching[0].page})"

    else:
        raise DocumentProcessingError(
            "Veuillez spécifier soit 'chunk_index', soit 'page', soit 'passage_text'."
        )

    explanation = chain_explain(passage=target_passage, context=surrounding_context)

    return ExplanationResult(
        document_id=document_id,
        explanation=explanation,
        passage=target_passage,
    )
