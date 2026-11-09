import sys
from pathlib import Path

from app.core.exceptions import AppError
from app.core.logging import setup_logging
from app.document_processing.detector import detect_format
from app.document_processing.loaders import load_sections


def main() -> int:
    sys.stdout.reconfigure(errors="replace")  # évite les plantages d'encodage dans CMD
    if len(sys.argv) != 2:
        print('Usage : python try_extract.py "<chemin_du_fichier>"')
        return 1

    setup_logging()
    path = Path(sys.argv[1])
    try:
        print(f"Format détecté : {detect_format(path).value}")
        sections = chars = 0
        for section in load_sections(path):
            sections += 1
            chars += len(section.text)
            if sections <= 2:
                print(f"\n--- section {sections} | page={section.page} | {section.location} ---")
                print(section.text[:300])
        print(f"\nTotal : {sections} sections, {chars} caractères")
    except AppError as exc:
        print(f"Erreur [{exc.code}] : {exc.message}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())