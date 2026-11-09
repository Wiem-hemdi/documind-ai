class AppError(Exception):
    """Erreur métier de base, convertie en réponse JSON par main.py."""

    status_code: int = 500
    code: str = "internal_error"

    def __init__(self, message: str = "Erreur interne du service."):
        super().__init__(message)
        self.message = message


class NotFoundError(AppError):
    status_code = 404
    code = "not_found"


class UnsupportedFileTypeError(AppError):
    status_code = 415
    code = "unsupported_file_type"


class FileTooLargeError(AppError):
    status_code = 413
    code = "file_too_large"


class DocumentProcessingError(AppError):
    status_code = 422
    code = "document_processing_error"


class VectorStoreError(AppError):
    status_code = 503
    code = "vector_store_unavailable"


class LLMError(AppError):
    status_code = 503
    code = "llm_unavailable"