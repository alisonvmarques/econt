"""Valores em reais, guardados como centavos inteiros para não perder precisão."""

from __future__ import annotations

import re


class ValorInvalido(ValueError):
    pass


def ler_reais(texto: str) -> int:
    """Converte "R$ 25.000,00", "25000" ou "25.000,5" em centavos.

    O ponto separa milhares e a vírgula separa os centavos, como se escreve no Brasil.
    """
    limpo = texto.replace("R$", "").replace(" ", "").replace(" ", "").strip()
    if not limpo:
        raise ValorInvalido("Informe o valor.")
    if limpo.startswith("-"):
        raise ValorInvalido("O valor não pode ser negativo.")
    inteiro, _, decimal = limpo.partition(",")
    if "," in decimal:
        raise ValorInvalido("Use a vírgula só para os centavos, assim: 25.000,00.")
    if not re.fullmatch(r"\d{1,3}(\.\d{3})*|\d+", inteiro) or not re.fullmatch(r"\d{0,2}", decimal):
        raise ValorInvalido("Valor inválido. Escreva assim: 25.000,00.")
    centavos = int(inteiro.replace(".", "")) * 100
    if decimal:
        centavos += int(decimal.ljust(2, "0"))
    return centavos


def formatar_reais(centavos: int) -> str:
    """1000000 → "R$ 10.000,00"."""
    reais, resto = divmod(centavos, 100)
    milhares = f"{reais:,}".replace(",", ".")
    return f"R$ {milhares},{resto:02d}"
