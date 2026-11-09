"""Route de comparaison multi-documents."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from starlette.concurrency import run_in_threadpool

from app.api.dependencies import get_user_id, require_internal_api_key
from app.api.schemas import CompareRequest, CompareResponse
from app.services.advanced_service import compare_user_documents

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/compare",
    tags=["compare"],
    dependencies=[Depends(require_internal_api_key)],
)


@router.post("", response_model=CompareResponse)
async def compare(
    payload: CompareRequest,
    user_id: str = Depends(get_user_id),
) -> CompareResponse:
    """Compare plusieurs documents appartenant à l'utilisateur."""
    result = await run_in_threadpool(
        compare_user_documents,
        user_id=user_id,
        document_ids=payload.document_ids,
        question=payload.question,
    )

    return CompareResponse(
        document_ids=result.document_ids,
        comparison=result.comparison,
    )
