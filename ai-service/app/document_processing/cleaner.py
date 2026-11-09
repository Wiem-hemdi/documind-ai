"""Nettoyage et normalisation du texte brut issu des loaders.

Préserve les accents, l'arabe et tout caractère Unicode légitime.
Supprime les artefacts d'extraction (césures, caractères de contrôle,
espaces multiples).
"""

import re
import unicodedata

# Caractères de contrôle à supprimer (on garde \n et \t)
_CONTROL_RE = re.compile(
    r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]",
)

# Césure en fin de ligne : « mot-\n » → « mot »
# On ne rejoint que si le caractère suivant est une minuscule (évite de
# casser « self-\nservice » quand la ligne est simplement longue).
_HYPHEN_RE = re.compile(r"(\w)-\s*\n\s*([a-zà-öù-ÿ\u0600-\u06ff])")

# Espaces horizontaux multiples → un seul espace
_MULTI_SPACE_RE = re.compile(r"[^\S\n]+")

# Plus de deux sauts de ligne consécutifs → deux maximum
_MULTI_NEWLINE_RE = re.compile(r"\n{3,}")


def clean_text(raw: str) -> str:
    """Nettoie et normalise un texte brut.

    1. Normalisation Unicode NFC (accents composés).
    2. Suppression des caractères de contrôle (sauf \\n, \\t).
    3. Réparation des césures de fin de ligne.
    4. Normalisation des espaces horizontaux.
    5. Limitation des sauts de ligne consécutifs.
    6. Strip final.
    """
    if not raw:
        return ""

    # 1. NFC : assure que « é » est un seul codepoint, pas e + accent
    text = unicodedata.normalize("NFC", raw)

    # 2. Suppression des caractères de contrôle
    text = _CONTROL_RE.sub("", text)

    # 3. Réparation des césures
    text = _HYPHEN_RE.sub(r"\1\2", text)

    # 4. Espaces horizontaux multiples → un seul
    text = _MULTI_SPACE_RE.sub(" ", text)

    # 5. Sauts de ligne excessifs
    text = _MULTI_NEWLINE_RE.sub("\n\n", text)

    # 6. Strip
    return text.strip()
