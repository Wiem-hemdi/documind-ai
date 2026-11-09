"""Schémas Pydantic pour la validation des requêtes et réponses de l'API."""

from __future__ import annotations

from pydantic import BaseModel, Field


# --- Chat ---
class ChatMessage(BaseModel):
    role: str = Field(..., description="Rôle de l'émetteur : 'user' ou 'assistant'")
    content: str = Field(..., min_length=1, max_length=4000)


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    history: list[ChatMessage] = Field(default_factory=list)
    document_ids: list[str] | None = Field(
        default=None,
        description="Filtrer optionnellement sur une liste de documents spécifiques",
    )


class SourceResponse(BaseModel):
    id: int
    filename: str
    page: int | None
    location: str | None
    text_snippet: str
    score: float


class ChatResponse(BaseModel):
    answer: str
    sources: list[SourceResponse] = Field(default_factory=list)
    reformulated_question: str | None = None
    has_relevant_context: bool = True


# --- Documents ---
class DocumentInfoResponse(BaseModel):
    document_id: str
    filename: str
    chunk_count: int


class IndexResponse(BaseModel):
    document_id: str
    filename: str
    chunk_count: int
    was_reindexed: bool


class DeleteDocumentResponse(BaseModel):
    status: str = "deleted"
    document_id: str


# --- Fonctions avancées ---
class SummaryResponse(BaseModel):
    document_id: str
    filename: str
    summary: str
    chunk_count: int


class ExtractInfoResponse(BaseModel):
    document_id: str
    filename: str
    extracted_info: str


class CompareRequest(BaseModel):
    document_ids: list[str] = Field(..., min_length=2)
    question: str = Field(default="", max_length=1000)


class CompareResponse(BaseModel):
    document_ids: list[str]
    comparison: str


class ExplainRequest(BaseModel):
    page: int | None = None
    chunk_index: int | None = None
    passage_text: str | None = None


class ExplainResponse(BaseModel):
    document_id: str
    passage: str
    explanation: str
