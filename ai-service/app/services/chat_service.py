"""Service de question-réponse RAG.

Pipeline :
1. Reformulation de question avec historique si présent.
2. Embedding de la question.
3. Recherche dans Qdrant avec filtre strict par `user_id` (+ document_ids optionnels).
4. Filtrage par seuil de pertinence `RELEVANCE_THRESHOLD`.
5. Si aucun chunk pertinent : réponse directe sans appeler le LLM.
6. Sinon : construction du prompt, appel LLM et renvoi de la réponse avec sources traçables.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from app.core.config import settings
from app.embeddings.embedding_service import embed_query
from app.rag.chains import qa, reformulate
from app.rag.vector_store import ScoredChunk, search

logger = logging.getLogger(__name__)

NO_RELEVANT_INFO_MESSAGE = (
    "L'information demandée ne figure pas dans les documents disponibles."
)


@dataclass(frozen=True)
class ChatSource:
    """Source d'information issue des chunks trouvés."""

    id: int
    filename: str
    page: int | None
    location: str | None
    text_snippet: str
    score: float


@dataclass(frozen=True)
class ChatResult:
    """Résultat de la question-réponse RAG."""

    answer: str
    sources: list[ChatSource] = field(default_factory=list)
    reformulated_question: str | None = None
    has_relevant_context: bool = True


def ask_question(
    question: str,
    user_id: str,
    history: list[dict] | None = None,
    document_ids: list[str] | None = None,
) -> ChatResult:
    """Traite une question utilisateur en RAG.

    Args:
        question: Question de l'utilisateur.
        user_id: Identifiant de l'utilisateur (obligatoire, isolation des données).
        history: Historique de conversation (facultatif).
        document_ids: Restriction optionnelle à certains documents.

    Returns:
        ChatResult contenant la réponse générée et les sources citées.
    """
    clean_q = question.strip()
    if not clean_q:
        return ChatResult(
            answer="Veuillez poser une question non vide.",
            has_relevant_context=False,
        )

    # 1. Reformulation si un historique existe
    reformulated_q = clean_q
    if history:
        try:
            reformulated_q = reformulate(clean_q, history)
            logger.info("Question reformulée : '%s' -> '%s'", clean_q, reformulated_q)
        except Exception as exc:
            logger.warning("Échec de reformulation, utilisation de la question brute : %s", exc)
            reformulated_q = clean_q

    # 2. Embedding de la question
    query_vector = embed_query(reformulated_q)

    # 3. Recherche Qdrant avec filtre strict user_id
    raw_results: list[ScoredChunk] = search(
        embedding=query_vector,
        user_id=user_id,
        top_k=settings.retrieval_top_k,
        document_ids=document_ids,
    )

    # 4. Filtrage par seuil de pertinence
    threshold = settings.relevance_threshold
    relevant_chunks = [c for c in raw_results if c.score >= threshold]

    logger.info(
        "Recherche pour user=%s : %d chunks trouvés, %d au-dessus du seuil (%.2f)",
        user_id,
        len(raw_results),
        len(relevant_chunks),
        threshold,
    )

    # 5. Si aucun chunk n'atteint le seuil : court-circuit sans appel LLM
    if not relevant_chunks:
        return ChatResult(
            answer=NO_RELEVANT_INFO_MESSAGE,
            sources=[],
            reformulated_question=reformulated_q if reformulated_q != clean_q else None,
            has_relevant_context=False,
        )

    # 6. Construction du contexte et des sources
    context_blocks: list[str] = []
    sources: list[ChatSource] = []

    for idx, chunk in enumerate(relevant_chunks, start=1):
        loc_str = chunk.location or (f"Page {chunk.page}" if chunk.page is not None else chunk.filename)
        context_blocks.append(
            f"[Source {idx} — {chunk.filename} ({loc_str})]\n{chunk.text}"
        )
        sources.append(
            ChatSource(
                id=idx,
                filename=chunk.filename,
                page=chunk.page,
                location=chunk.location,
                text_snippet=chunk.text[:200] + ("..." if len(chunk.text) > 200 else ""),
                score=chunk.score,
            )
        )

    context_text = "\n\n".join(context_blocks)

    # 7. Appel LLM
    answer = qa(question=reformulated_q, context=context_text)

    return ChatResult(
        answer=answer,
        sources=sources,
        reformulated_question=reformulated_q if reformulated_q != clean_q else None,
        has_relevant_context=True,
    )
