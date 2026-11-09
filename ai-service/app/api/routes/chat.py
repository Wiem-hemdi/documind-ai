"""Route de question-réponse RAG interactive."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from starlette.concurrency import run_in_threadpool

from app.api.dependencies import get_user_id, require_internal_api_key
from app.api.schemas import ChatRequest, ChatResponse, SourceResponse
from app.services.chat_service import ask_question

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/chat",
    tags=["chat"],
    dependencies=[Depends(require_internal_api_key)],
)


@router.post("", response_model=ChatResponse)
async def chat(
    payload: ChatRequest,
    user_id: str = Depends(get_user_id),
) -> ChatResponse:
    """Interroge la base documentaire en RAG selon la question et l'historique."""
    history_dicts = [{"role": m.role, "content": m.content} for m in payload.history]

    result = await run_in_threadpool(
        ask_question,
        question=payload.question,
        user_id=user_id,
        history=history_dicts,
        document_ids=payload.document_ids,
    )

    return ChatResponse(
        answer=result.answer,
        sources=[
            SourceResponse(
                id=s.id,
                filename=s.filename,
                page=s.page,
                location=s.location,
                text_snippet=s.text_snippet,
                score=round(s.score, 4),
            )
            for s in result.sources
        ],
        reformulated_question=result.reformulated_question,
        has_relevant_context=result.has_relevant_context,
    )
