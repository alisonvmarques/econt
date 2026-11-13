"""Formatação enquanto se digita (RNF16): CNPJ, CPF, telefone e data.

Cada função recebe o texto como está no campo, talvez pela metade, e devolve o mesmo texto
com a pontuação no lugar. O separador só entra quando já existe o caractere seguinte, para
o Backspace apagar normalmente. Texto que não parece o formato (por exemplo, um telefone com
"ramal") volta como veio.
"""

from __future__ import annotations

import re


def _montar(caracteres: str, separadores: dict[int, str]) -> str:
    """Põe `separadores[i]` antes do caractere de índice i."""
    return "".join(separadores.get(i, "") + c for i, c in enumerate(caracteres))


def cnpj_ao_digitar(texto: str) -> str:
    """00.000.000/0000-00, aceitando as letras do CNPJ alfanumérico."""
    caracteres = "".join(c for c in texto.upper() if c.isalnum())[:14]
    return _montar(caracteres, {2: ".", 5: ".", 8: "/", 12: "-"})


def cpf_ao_digitar(texto: str) -> str:
    """000.000.000-00. Com letras, não é CPF: volta como veio."""
    if re.search(r"[^\d.\-\s]", texto):
        return texto
    return _montar(re.sub(r"\D", "", texto)[:11], {3: ".", 6: ".", 9: "-"})


def documento_ao_digitar(tipo: str, texto: str) -> str:
    return cpf_ao_digitar(texto) if tipo == "pf" else cnpj_ao_digitar(texto)


def telefone_ao_digitar(texto: str) -> str:
    """(00) 0000-0000 ou, com 11 números, (00) 00000-0000.

    Começando com + (internacional) ou 0 (0800), ou com letras, volta como veio."""
    if re.search(r"[^\d()\s-]", texto):
        return texto
    numeros = re.sub(r"\D", "", texto)
    if numeros.startswith("0"):
        return texto
    numeros = numeros[:11]
    if len(numeros) <= 2:
        return f"({numeros}" if numeros else ""
    ddd, resto = numeros[:2], numeros[2:]
    corte = 5 if len(numeros) == 11 else 4
    if len(resto) > corte:
        resto = f"{resto[:corte]}-{resto[corte:]}"
    return f"({ddd}) {resto}"


def data_ao_digitar(texto: str) -> str:
    """dd/mm/aaaa. Dia ou mês de um número seguido de barra ganha o zero: 5/1 vira 05/01."""
    if re.search(r"[^\d/\s]", texto):
        return texto
    partes = re.sub(r"\s", "", texto).split("/")
    partes = [
        parte.zfill(2) if indice < min(2, len(partes) - 1) and len(parte) == 1 else parte
        for indice, parte in enumerate(partes)
    ]
    return _montar("".join(partes)[:8], {2: "/", 4: "/"})


def chave_pix_ao_digitar(tipo: str, texto: str) -> str:
    if tipo == "cpf":
        return cpf_ao_digitar(texto)
    if tipo == "cnpj":
        return cnpj_ao_digitar(texto)
    if tipo == "telefone":
        return telefone_ao_digitar(texto)
    return texto
