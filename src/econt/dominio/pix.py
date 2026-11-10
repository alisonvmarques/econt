"""Chaves Pix: cada chave só é aceita no formato do seu tipo (RN02).

As chaves são guardadas como o Banco Central as registra: CPF e CNPJ só com os caracteres,
e-mail em minúsculas, telefone no formato +55 com DDD e chave aleatória em minúsculas.
"""

from __future__ import annotations

import re

from econt.dominio.documentos import (
    cnpj_valido,
    cpf_valido,
    formatar_cnpj,
    formatar_cpf,
    somente_caracteres,
)

TIPOS_DE_CHAVE = {
    "cnpj": "CNPJ",
    "cpf": "CPF",
    "email": "E-mail",
    "telefone": "Telefone",
    "aleatoria": "Aleatória",
}
EMAIL = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9\-]+(\.[A-Za-z0-9\-]+)+")
ALEATORIA = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")
TAMANHO_MAXIMO_EMAIL = 77


class ChaveInvalida(ValueError):
    pass


def normalizar_chave(tipo: str, chave: str) -> str:
    """Devolve a chave como é guardada, ou levanta ChaveInvalida dizendo o que corrigir."""
    chave = chave.strip()
    if tipo not in TIPOS_DE_CHAVE:
        raise ChaveInvalida("Escolha o tipo da chave.")
    if not chave:
        raise ChaveInvalida("Informe a chave.")
    if tipo == "cpf":
        if not cpf_valido(chave):
            raise ChaveInvalida("CPF inválido: confira os 11 números.")
        return somente_caracteres(chave)
    if tipo == "cnpj":
        if not cnpj_valido(chave):
            raise ChaveInvalida("CNPJ inválido: confira os 14 caracteres.")
        return somente_caracteres(chave)
    if tipo == "email":
        if len(chave) > TAMANHO_MAXIMO_EMAIL or not EMAIL.fullmatch(chave):
            raise ChaveInvalida("E-mail inválido. Escreva assim: financeiro@exemplo.com.br.")
        return chave.lower()
    if tipo == "telefone":
        numeros = re.sub(r"\D", "", chave)
        if chave.startswith("+"):
            if not numeros.startswith("55"):
                raise ChaveInvalida("O Pix aceita só telefone do Brasil (+55).")
            numeros = numeros[2:]
        if len(numeros) not in (10, 11) or numeros[0] == "0":
            raise ChaveInvalida("Telefone com DDD, assim: (81) 99999-0000.")
        return f"+55{numeros}"
    if not ALEATORIA.fullmatch(chave.lower()):
        raise ChaveInvalida(
            "A chave aleatória tem 36 caracteres, assim: 1a2b3c4d-1a2b-1a2b-1a2b-1a2b3c4d5e6f."
        )
    return chave.lower()


def formatar_chave(tipo: str, chave: str) -> str:
    """Como a chave aparece na tela e na impressão."""
    if tipo == "cpf":
        return formatar_cpf(chave)
    if tipo == "cnpj":
        return formatar_cnpj(chave)
    if tipo == "telefone" and chave.startswith("+55") and len(chave) in (13, 14):
        ddd, numero = chave[3:5], chave[5:]
        return f"({ddd}) {numero[:-4]}-{numero[-4:]}"
    return chave
