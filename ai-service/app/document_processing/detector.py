import zipfile
from pathlib import Path

from app.core.exceptions import UnsupportedFileTypeError
from app.document_processing.models import DocumentFormat

_EXTENSIONS: dict[str, DocumentFormat] = {
    ".pdf": DocumentFormat.PDF,
    ".docx": DocumentFormat.DOCX,
    ".txt": DocumentFormat.TXT,
    ".md": DocumentFormat.MD,
    ".csv": DocumentFormat.CSV,
    ".xlsx": DocumentFormat.XLSX,
    ".pptx": DocumentFormat.PPTX,
}

_LEGACY_OFFICE = {".doc", ".xls", ".ppt"}

# Fichier interne qui prouve qu'une archive zip est bien un document Office
_OOXML_MARKERS: dict[DocumentFormat, str] = {
    DocumentFormat.DOCX: "word/document.xml",
    DocumentFormat.XLSX: "xl/workbook.xml",
    DocumentFormat.PPTX: "ppt/presentation.xml",
}

SUPPORTED_EXTENSIONS = sorted(_EXTENSIONS)


def detect_format(path: Path) -> DocumentFormat:
    """Détermine le format du fichier et vérifie que son contenu correspond."""
    ext = path.suffix.lower()

    if ext in _LEGACY_OFFICE:
        raise UnsupportedFileTypeError(
            "Les anciens formats Office (.doc, .xls, .ppt) ne sont pas pris en charge. "
            "Enregistrez le fichier en .docx, .xlsx ou .pptx."
        )

    fmt = _EXTENSIONS.get(ext)
    if fmt is None:
        shown = ext or "sans extension"
        raise UnsupportedFileTypeError(
            f"Format non pris en charge : {shown}. "
            f"Formats acceptés : {', '.join(SUPPORTED_EXTENSIONS)}."
        )

    _verify_content(path, fmt)
    return fmt


def _mismatch(ext: str) -> UnsupportedFileTypeError:
    return UnsupportedFileTypeError(
        f"Le contenu du fichier ne correspond pas à son extension ({ext})."
    )


def _verify_content(path: Path, fmt: DocumentFormat) -> None:
    ext = path.suffix.lower()
    with path.open("rb") as f:
        head = f.read(8192)

    if fmt is DocumentFormat.PDF:
        if b"%PDF" not in head[:1024]:
            raise _mismatch(ext)
    elif fmt in _OOXML_MARKERS:
        try:
            with zipfile.ZipFile(path) as archive:
                if _OOXML_MARKERS[fmt] not in archive.namelist():
                    raise _mismatch(ext)
        except zipfile.BadZipFile:
            raise _mismatch(ext) from None
    else:  # texte : un octet nul indique un fichier binaire
        if b"\x00" in head:
            raise _mismatch(ext)