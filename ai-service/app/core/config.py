from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# ai-service/ (config.py -> core -> app -> ai-service)
BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- Application ---
    app_name: str = "DocuMind AI Service"
    app_env: str = "development"
    log_level: str = "INFO"

    # --- Qdrant ---
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: SecretStr | None = None
    qdrant_collection: str = "documind_chunks"

    # --- Ollama ---
    ollama_base_url: str = "http://localhost:11434"
    llm_model: str = "qwen2.5:7b"
    llm_temperature: float = Field(default=0.1, ge=0.0, le=2.0)
    embedding_model: str = "bge-m3"
    embedding_dimension: int = Field(default=1024, gt=0)

    # --- Traitement des documents ---
    chunk_size: int = Field(default=1000, gt=0)
    chunk_overlap: int = Field(default=150, ge=0)
    embed_batch_size: int = Field(default=32, gt=0)
    max_upload_mb: int = Field(default=50, gt=0)

    # --- RAG ---
    retrieval_top_k: int = Field(default=5, gt=0, le=50)
    relevance_threshold: float = Field(default=0.55, ge=0.0, le=1.0)

    # --- Sécurité ---
    internal_api_key: SecretStr = SecretStr("change-me")

    @model_validator(mode="after")
    def check_chunking(self) -> "Settings":
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("CHUNK_OVERLAP doit être inférieur à CHUNK_SIZE")
        return self

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()