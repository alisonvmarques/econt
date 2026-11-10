"""Dados da entidade, quem paga (RF15, RF16, RN09)."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime

from econt.dominio.documentos import cnpj_valido, formatar_cnpj, somente_caracteres


class EntidadeInvalida(ValueError):
    pass


@dataclass
class Entidade:
    razao_social: str
    cnpj: str
    logo: bytes | None = None

    @property
    def cnpj_formatado(self) -> str:
        return formatar_cnpj(self.cnpj)


def problemas_da_entidade(razao_social: str, cnpj: str) -> dict[str, str]:
    """Erros por campo, em português. Vazio quando está tudo certo."""
    erros = {}
    if not razao_social.strip():
        erros["razao_social"] = "Informe a razão social."
    if not somente_caracteres(cnpj):
        erros["cnpj"] = "Informe o CNPJ."
    elif not cnpj_valido(cnpj):
        erros["cnpj"] = "CNPJ inválido: confira os dois últimos dígitos."
    return erros


def obter_entidade(conexao: sqlite3.Connection) -> Entidade | None:
    linha = conexao.execute("SELECT razao_social, cnpj, logo FROM entidade WHERE id = 1").fetchone()
    return Entidade(*linha) if linha else None


def salvar_entidade(conexao: sqlite3.Connection, entidade: Entidade) -> None:
    """Cria ou atualiza a única entidade do ECont."""
    erros = problemas_da_entidade(entidade.razao_social, entidade.cnpj)
    if erros:
        raise EntidadeInvalida(" ".join(erros.values()))
    agora = datetime.now().isoformat(timespec="seconds")
    with conexao:
        conexao.execute(
            """
            INSERT INTO entidade (id, razao_social, cnpj, logo, criado_em, alterado_em)
            VALUES (1, ?, ?, ?, ?, ?)
            ON CONFLICT (id) DO UPDATE SET razao_social = excluded.razao_social,
                cnpj = excluded.cnpj, logo = excluded.logo, alterado_em = excluded.alterado_em
            """,
            (
                entidade.razao_social.strip(),
                somente_caracteres(entidade.cnpj),
                entidade.logo,
                agora,
                agora,
            ),
        )
