from dataclasses import dataclass
from enum import Enum


class DocumentFormat(str, Enum):
    PDF = "pdf"
    DOCX = "docx"
    TXT = "txt"
    MD = "md"
    CSV = "csv"
    XLSX = "xlsx"
    PPTX = "pptx"


@dataclass(frozen=True)
class ExtractedSection:
    """Un morceau de texte extrait d'un document.

    page     : numéro de page (PDF) ou de diapositive (PPTX), sinon None.
    location : repère lisible pour les sources (« Feuille « Ventes », lignes 2-51 »).
    """

    text: str
    page: int | None = None
    location: str | None = None