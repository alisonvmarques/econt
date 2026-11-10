"""Comparação de textos sem diferenciar maiúsculas e acentos (RF02)."""

from __future__ import annotations

import unicodedata


def _base(caractere: str) -> str:
    """ "Á" vira "a". Sempre devolve um caractere, para as posições baterem com o original."""
    simples = unicodedata.normalize("NFKD", caractere)[:1] or caractere
    return simples.lower()[:1]


def normalizar(texto: str) -> str:
    """Mesmo tamanho do texto original: cada caractere vira sua letra base minúscula."""
    return "".join(_base(c) for c in texto)


def encontrar(texto: str, termo: str) -> tuple[int, int] | None:
    """Posição do termo no texto (início e fim), sem diferenciar maiúsculas e acentos."""
    termo = normalizar(termo.strip())
    if not termo:
        return None
    inicio = normalizar(texto).find(termo)
    return None if inicio < 0 else (inicio, inicio + len(termo))
