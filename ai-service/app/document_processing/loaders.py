import codecs
import csv
import io
import logging
import shutil
from collections.abc import Callable, Iterable, Iterator
from pathlib import Path

import chardet

from app.core.exceptions import AppError, DocumentProcessingError, NotFoundError
from app.document_processing.detector import detect_format
from app.document_processing.models import DocumentFormat, ExtractedSection

logger = logging.getLogger(__name__)

TEXT_BLOCK_CHARS = 4000   # taille approximative d'une section pour les textes
ROWS_PER_SECTION = 50     # lignes regroupées par section pour CSV / XLSX
MIN_NATIVE_PDF_TEXT_CHARS = 30


# --------------------------------------------------------------------------
# Utilitaires
# --------------------------------------------------------------------------
def _buffered(lines: Iterable[str], limit: int = TEXT_BLOCK_CHARS) -> Iterator[str]:
    """Regroupe des lignes en blocs d'environ `limit` caractères."""
    buffer: list[str] = []
    size = 0
    for line in lines:
        buffer.append(line)
        size += len(line)
        if size >= limit:
            yield "\n".join(buffer)
            buffer, size = [], 0
    if buffer:
        yield "\n".join(buffer)


def _detect_encoding(path: Path) -> str:
    with path.open("rb") as f:
        raw = f.read(100_000)
    try:
        # décodeur incrémental : tolère un caractère coupé à la fin de l'échantillon
        codecs.getincrementaldecoder("utf-8")().decode(raw, final=False)
        return "utf-8-sig"  # gère aussi le BOM
    except UnicodeDecodeError:
        guess = chardet.detect(raw).get("encoding")
        return guess or "cp1252"


def _location(label: str | None, start: int, end: int) -> str:
    rows = f"lignes {start}-{end}"
    return f"{label}, {rows}" if label else rows


def _rows_to_sections(
    header: list[str], rows: Iterable[Iterable], label: str | None = None
) -> Iterator[ExtractedSection]:
    """Transforme des lignes de tableau en texte « colonne: valeur ; ... ».

    Chaque ligne est ainsi compréhensible seule, même une fois découpée en chunks.
    """
    buffer: list[str] = []
    start = 2
    row_no = 1  # la ligne 1 est l'en-tête
    for row in rows:
        row_no += 1
        pairs = [
            f"{name}: {value}"
            for name, value in zip(header, row)
            if value is not None and str(value).strip()
        ]
        if not pairs:
            continue
        if not buffer:
            start = row_no
        buffer.append(" ; ".join(pairs))
        if len(buffer) >= ROWS_PER_SECTION:
            yield ExtractedSection("\n".join(buffer), location=_location(label, start, row_no))
            buffer = []
    if buffer:
        yield ExtractedSection("\n".join(buffer), location=_location(label, start, row_no))


def _clean_header(cells: Iterable) -> list[str]:
    return [
        str(c).strip() if c is not None and str(c).strip() else f"colonne_{i + 1}"
        for i, c in enumerate(cells)
    ]


# --------------------------------------------------------------------------
# Lecteurs par format
# --------------------------------------------------------------------------
def _load_pdf(path: Path) -> Iterator[ExtractedSection]:
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    if reader.is_encrypted and not reader.decrypt(""):
        raise DocumentProcessingError("Le PDF est protégé par un mot de passe.")

    ocr_document = None
    try:
        for number, page in enumerate(reader.pages, start=1):
            try:
                text = page.extract_text() or ""
            except Exception:
                logger.warning("Page %s illisible dans %s, OCR tenté", number, path.name)
                text = ""

            if len(text.strip()) < MIN_NATIVE_PDF_TEXT_CHARS:
                if ocr_document is None:
                    if shutil.which("tesseract") is None:
                        raise DocumentProcessingError(
                            "Cette page semble être un scan, mais Tesseract OCR n'est pas installé. "
                            "Installez Tesseract avec les langues française et anglaise, puis "
                            "redémarrez le service IA."
                        )
                    import pymupdf
                    import pytesseract
                    from PIL import Image

                    ocr_document = pymupdf.open(str(path))

                pixmap = ocr_document[number - 1].get_pixmap(
                    matrix=pymupdf.Matrix(2.5, 2.5),
                    alpha=False,
                )
                with Image.open(io.BytesIO(pixmap.tobytes("png"))) as image:
                    try:
                        ocr_text = pytesseract.image_to_string(image, lang="fra+eng").strip()
                    except pytesseract.TesseractError as exc:
                        raise DocumentProcessingError(
                            "Tesseract n'a pas pu analyser cette page. Vérifiez que les données "
                            "de langue française et anglaise sont installées."
                        ) from exc
                if ocr_text:
                    text = ocr_text

            yield ExtractedSection(text=text, page=number)
    finally:
        if ocr_document is not None:
            ocr_document.close()

def _load_docx(path: Path) -> Iterator[ExtractedSection]:
    from docx import Document
    from docx.table import Table
    from docx.text.paragraph import Paragraph

    doc = Document(str(path))

    def blocks() -> Iterator[str]:
        # On suit l'ordre réel du document (paragraphes et tableaux mélangés)
        for child in doc.element.body.iterchildren():
            tag = child.tag.rsplit("}", 1)[-1]
            if tag == "p":
                text = Paragraph(child, doc).text.strip()
                if text:
                    yield text
            elif tag == "tbl":
                for row in Table(child, doc).rows:
                    line = " | ".join(c.text.strip() for c in row.cells if c.text.strip())
                    if line:
                        yield line

    for block in _buffered(blocks()):
        yield ExtractedSection(text=block)


def _load_text(path: Path) -> Iterator[ExtractedSection]:
    encoding = _detect_encoding(path)
    with path.open("r", encoding=encoding, errors="replace") as f:
        for block in _buffered(line.rstrip("\r\n") for line in f):
            yield ExtractedSection(text=block)


def _load_csv(path: Path) -> Iterator[ExtractedSection]:
    encoding = _detect_encoding(path)
    with path.open("r", encoding=encoding, errors="replace", newline="") as f:
        sample = f.read(8192)
        f.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
        except csv.Error:
            dialect = csv.excel
        reader = csv.reader(f, dialect)
        first = next(reader, None)
        if first is None:
            return
        yield from _rows_to_sections(_clean_header(first), reader)


def _load_xlsx(path: Path) -> Iterator[ExtractedSection]:
    from openpyxl import load_workbook

    workbook = load_workbook(filename=str(path), read_only=True, data_only=True)
    try:
        for sheet in workbook.worksheets:
            rows = sheet.iter_rows(values_only=True)
            first = next(rows, None)
            if first is None:
                continue
            yield from _rows_to_sections(
                _clean_header(first), rows, label=f"Feuille « {sheet.title} »"
            )
    finally:
        workbook.close()


def _shape_text(shape) -> Iterator[str]:
    from pptx.enum.shapes import MSO_SHAPE_TYPE

    if shape.shape_type == MSO_SHAPE_TYPE.GROUP:
        for child in shape.shapes:
            yield from _shape_text(child)
        return
    if shape.has_text_frame:
        text = shape.text_frame.text.strip()
        if text:
            yield text
    if shape.has_table:
        for row in shape.table.rows:
            line = " | ".join(c.text.strip() for c in row.cells if c.text.strip())
            if line:
                yield line


def _load_pptx(path: Path) -> Iterator[ExtractedSection]:
    from pptx import Presentation

    presentation = Presentation(str(path))
    for number, slide in enumerate(presentation.slides, start=1):
        parts: list[str] = []
        for shape in slide.shapes:
            parts.extend(_shape_text(shape))
        if slide.has_notes_slide and slide.notes_slide.notes_text_frame is not None:
            notes = slide.notes_slide.notes_text_frame.text.strip()
            if notes:
                parts.append(f"Notes : {notes}")
        yield ExtractedSection(
            text="\n".join(parts), page=number, location=f"Diapositive {number}"
        )


_LOADERS: dict[DocumentFormat, Callable[[Path], Iterator[ExtractedSection]]] = {
    DocumentFormat.PDF: _load_pdf,
    DocumentFormat.DOCX: _load_docx,
    DocumentFormat.TXT: _load_text,
    DocumentFormat.MD: _load_text,
    DocumentFormat.CSV: _load_csv,
    DocumentFormat.XLSX: _load_xlsx,
    DocumentFormat.PPTX: _load_pptx,
}


# --------------------------------------------------------------------------
# Point d'entrée
# --------------------------------------------------------------------------
def _iterate(path: Path, fmt: DocumentFormat) -> Iterator[ExtractedSection]:
    count = 0
    try:
        for section in _LOADERS[fmt](path):
            if section.text.strip():
                count += 1
                yield section
    except AppError:
        raise
    except Exception as exc:
        logger.exception("Échec de lecture de %s (%s)", path.name, fmt.value)
        raise DocumentProcessingError(
            f"Impossible de lire le fichier {fmt.value.upper()} : il est corrompu ou illisible."
        ) from exc

    if count == 0:
        raise DocumentProcessingError(
            "Aucun texte exploitable n'a été trouvé dans le document. Pour un PDF scanné, "
            "vérifiez que les pages sont lisibles et que Tesseract dispose des langues requises."
        )


def load_sections(path: str | Path) -> Iterator[ExtractedSection]:
    """Détecte le format puis renvoie un générateur de sections de texte.

    Les erreurs de format (fichier absent, type non supporté) sont levées
    immédiatement ; les erreurs de lecture pendant l'itération.
    """
    path = Path(path)
    if not path.is_file():
        raise NotFoundError("Fichier introuvable.")
    fmt = detect_format(path)
    logger.info("Lecture de %s (format %s)", path.name, fmt.value)
    return _iterate(path, fmt)