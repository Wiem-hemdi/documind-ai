"""Routes API de gestion des documents et fonctions documentaires avancées."""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, Header, UploadFile
from starlette.concurrency import run_in_threadpool

from app.api.dependencies import get_user_id, require_internal_api_key
from app.api.schemas import (
    DeleteDocumentResponse,
    DocumentInfoResponse,
    ExplainRequest,
    ExplainResponse,
    ExtractInfoResponse,
    IndexResponse,
    SummaryResponse,
)
from app.core.config import settings
from app.core.exceptions import FileTooLargeError
from app.document_processing.loaders import load_sections
from app.services.advanced_service import (
    explain_document_passage,
    extract_document_info,
    summarize_document,
)
from app.services.document_service import delete, list_documents, upload_and_index

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/documents",
    tags=["documents"],
    dependencies=[Depends(require_internal_api_key)],
)


async def _read_file_safe(file: UploadFile) -> bytes:
    """Lit le contenu d'un fichier uploadé en vérifiant la taille limite."""
    content = await file.read(settings.max_upload_bytes + 1)
    if len(content) > settings.max_upload_bytes:
        raise FileTooLargeError(
            f"Le fichier dépasse la limite autorisée de {settings.max_upload_mb} Mo."
        )
    return content


def _extract_raw_sections(content: bytes, filename: str) -> list[dict]:
    """Extraction simple en texte brut (pour l'endpoint /extract conservé)."""
    suffix = Path(filename).suffix.lower()
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / f"document{suffix}"
        path.write_bytes(content)
        return [
            {
                "text": section.text,
                "page": section.page,
                "location": section.location,
            }
            for section in load_sections(path)
        ]


# --------------------------------------------------------------------------
# Indexation & Gestion
# --------------------------------------------------------------------------
@router.post("", response_model=IndexResponse)
async def upload_document(
    file: UploadFile = File(...),
    document_id: str = Form(..., min_length=1, max_length=128),
    user_id_form: str | None = Form(None, alias="user_id"),
    x_user_id: str | None = Header(None, alias="X-User-Id"),
) -> IndexResponse:
    """Importe et indexe un document dans Qdrant avec ses embeddings."""
    user_id = user_id_form or x_user_id
    if not user_id:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=400,
            detail="L'identifiant utilisateur (user_id dans le formulaire ou X-User-Id) est requis.",
        )

    file_bytes = await _read_file_safe(file)
    filename = file.filename or "document"

    result = await run_in_threadpool(
        upload_and_index,
        file_content=file_bytes,
        filename=filename,
        user_id=user_id,
        document_id=document_id,
    )

    return IndexResponse(
        document_id=document_id,
        filename=filename,
        chunk_count=result.chunk_count,
        was_reindexed=result.was_reindexed,
    )


@router.get("", response_model=list[DocumentInfoResponse])
async def get_user_documents(
    user_id: str = Depends(get_user_id),
) -> list[DocumentInfoResponse]:
    """Liste tous les documents indexés pour l'utilisateur spécifié."""
    docs = await run_in_threadpool(list_documents, user_id=user_id)
    return [
        DocumentInfoResponse(
            document_id=d.document_id,
            filename=d.filename,
            chunk_count=d.chunk_count,
        )
        for d in docs
    ]


@router.delete("/{document_id}", response_model=DeleteDocumentResponse)
async def delete_document(
    document_id: str,
    user_id: str = Depends(get_user_id),
) -> DeleteDocumentResponse:
    """Supprime l'index d'un document pour l'utilisateur courant."""
    await run_in_threadpool(delete, user_id=user_id, document_id=document_id)
    return DeleteDocumentResponse(status="deleted", document_id=document_id)


# --------------------------------------------------------------------------
# Fonctions documentaires avancées
# --------------------------------------------------------------------------
@router.post("/{document_id}/summary", response_model=SummaryResponse)
async def get_summary(
    document_id: str,
    user_id: str = Depends(get_user_id),
) -> SummaryResponse:
    """Génère un résumé structuré du document par map-reduce."""
    res = await run_in_threadpool(
        summarize_document,
        user_id=user_id,
        document_id=document_id,
    )
    return SummaryResponse(
        document_id=res.document_id,
        filename=res.filename,
        summary=res.summary,
        chunk_count=res.chunk_count,
    )


@router.post("/{document_id}/extract-info", response_model=ExtractInfoResponse)
async def extract_key_information(
    document_id: str,
    user_id: str = Depends(get_user_id),
) -> ExtractInfoResponse:
    """Extrait les informations essentielles et données clés du document."""
    res = await run_in_threadpool(
        extract_document_info,
        user_id=user_id,
        document_id=document_id,
    )
    return ExtractInfoResponse(
        document_id=res.document_id,
        filename=res.filename,
        extracted_info=res.extracted_info,
    )


@router.post("/{document_id}/explain", response_model=ExplainResponse)
async def explain_passage(
    document_id: str,
    payload: ExplainRequest,
    user_id: str = Depends(get_user_id),
) -> ExplainResponse:
    """Explique pédagogiquement un passage ou une page ciblée d'un document."""
    res = await run_in_threadpool(
        explain_document_passage,
        user_id=user_id,
        document_id=document_id,
        page=payload.page,
        chunk_index=payload.chunk_index,
        passage_text=payload.passage_text,
    )
    return ExplainResponse(
        document_id=res.document_id,
        passage=res.passage,
        explanation=res.explanation,
    )


# --------------------------------------------------------------------------
# Endpoint historique conservé : extraction simple
# --------------------------------------------------------------------------
@router.post("/extract")
async def extract_document_text(file: UploadFile = File(...)) -> dict:
    """Extrait le texte brut du fichier sans l'indexer (conservé pour rétrocompatibilité)."""
    content = await _read_file_safe(file)
    sections = await run_in_threadpool(
        _extract_raw_sections, content, file.filename or "document"
    )
    blocks = []
    for s in sections:
        loc = s["location"] or (f"Page {s['page']}" if s["page"] is not None else None)
        prefix = f"[{loc}]\n" if loc else ""
        blocks.append(f"{prefix}{s['text']}")

    return {
        "content": "\n\n".join(blocks),
        "sections": sections,
        "truncated": False,
    }


# --------------------------------------------------------------------------
# Endpoints de rétrocompatibilité (consommés par le backend Node.js actuel)
# --------------------------------------------------------------------------
@router.delete("/index/{owner_id}/{document_id}")
async def remove_document_index_compat(owner_id: str, document_id: str) -> dict:
    """Supprime l'index d'un document (format URL backend Node.js)."""
    await run_in_threadpool(delete, user_id=owner_id, document_id=document_id)
    return {"status": "deleted", "document_id": document_id}


@router.post("/chat")
async def chat_about_document_compat(
    file: UploadFile = File(...),
    question: str = Form(..., min_length=1, max_length=2000),
    history: str = Form(default="[]", max_length=100_000),
    owner_id: str = Form(..., min_length=1, max_length=128),
    document_id: str = Form(..., min_length=1, max_length=128),
) -> dict:
    """Chat avec upload multipart (compatibilité backend Node.js)."""
    import json
    from app.services.chat_service import ask_question

    # 1. Vérification / Indexation idempotente
    file_bytes = await _read_file_safe(file)
    await run_in_threadpool(
        upload_and_index,
        file_content=file_bytes,
        filename=file.filename or "document",
        user_id=owner_id,
        document_id=document_id,
    )

    # 2. Décodage de l'historique
    try:
        submitted_history = json.loads(history)
    except Exception:
        submitted_history = []

    parsed_history = []
    if isinstance(submitted_history, list):
        for item in submitted_history[-12:]:
            if isinstance(item, dict) and item.get("role") in {"user", "assistant"}:
                content = str(item.get("content", "")).strip()
                if content:
                    parsed_history.append({"role": item["role"], "content": content[:4000]})

    # 3. Appel du service RAG
    result = await run_in_threadpool(
        ask_question,
        question=question.strip(),
        user_id=owner_id,
        history=parsed_history,
        document_ids=[document_id],
    )

    # 4. Formatage compatible backend
    sources = [
        {
            "id": s.id,
            "location": s.location or (f"Page {s.page}" if s.page is not None else s.filename),
        }
        for s in result.sources
    ]

    return {
        "answer": result.answer,
        "sources": sources,
        "truncated": False,
    }

