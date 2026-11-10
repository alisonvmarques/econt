"""Lista oficial de bancos do Banco Central, que vem junto com o ECont (RN13)."""

from __future__ import annotations

import csv
import io
import sqlite3
from dataclasses import dataclass
from importlib import resources

DATA_DA_LISTA = "2026-11-08"


@dataclass(frozen=True)
class Banco:
    codigo: str
    ispb: str
    nome: str


def bancos_oficiais() -> list[Banco]:
    texto = resources.files("econt.dados.recursos").joinpath("bancos.csv").read_text("utf-8")
    return [Banco(**linha) for linha in csv.DictReader(io.StringIO(texto))]


def carregar_bancos_oficiais(conexao: sqlite3.Connection) -> int:
    """Grava a lista oficial na base. Não mexe nos bancos cadastrados manualmente."""
    bancos = bancos_oficiais()
    with conexao:
        conexao.executemany(
            """
            INSERT INTO banco (codigo, ispb, nome, origem) VALUES (?, ?, ?, 'oficial')
            ON CONFLICT (codigo) DO UPDATE SET ispb = excluded.ispb, nome = excluded.nome
            WHERE banco.origem = 'oficial'
            """,
            [(b.codigo, b.ispb, b.nome) for b in bancos],
        )
    return len(bancos)


class BancoInvalido(ValueError):
    pass


@dataclass(frozen=True)
class BancoCadastrado:
    codigo: str
    nome: str
    origem: str

    @property
    def rotulo(self) -> str:
        return f"{self.codigo} · {self.nome}"


def listar_bancos(conexao: sqlite3.Connection, busca: str = "") -> list[BancoCadastrado]:
    """Bancos em ordem de código. A busca procura no código e no nome, sem diferenciar
    maiúsculas de minúsculas."""
    termo = f"%{busca.strip().lower()}%"
    linhas = conexao.execute(
        """
        SELECT codigo, nome, origem FROM banco
        WHERE codigo LIKE ? OR lower(nome) LIKE ?
        ORDER BY codigo
        """,
        (termo, termo),
    ).fetchall()
    return [BancoCadastrado(*linha) for linha in linhas]


def obter_banco(conexao: sqlite3.Connection, codigo: str) -> BancoCadastrado | None:
    linha = conexao.execute(
        "SELECT codigo, nome, origem FROM banco WHERE codigo = ?", (codigo,)
    ).fetchone()
    return BancoCadastrado(*linha) if linha else None


def normalizar_codigo(codigo: str) -> str:
    """O código de compensação tem 3 dígitos: "1" vira "001"."""
    return codigo.strip().zfill(3)


def problemas_do_banco(conexao: sqlite3.Connection, codigo: str, nome: str) -> dict[str, str]:
    erros = {}
    codigo = codigo.strip()
    if not codigo:
        erros["codigo"] = "Informe o código do banco."
    elif not codigo.isdigit() or len(codigo) > 3:
        erros["codigo"] = "O código tem até 3 números, como 001."
    elif existente := obter_banco(conexao, normalizar_codigo(codigo)):
        erros["codigo"] = f"O código {existente.codigo} já é do {existente.nome}."
    if not nome.strip():
        erros["nome"] = "Informe o nome do banco."
    return erros


def cadastrar_banco_manual(conexao: sqlite3.Connection, codigo: str, nome: str) -> BancoCadastrado:
    """RF26: banco que ainda não está na lista oficial. Código repetido não é aceito."""
    erros = problemas_do_banco(conexao, codigo, nome)
    if erros:
        raise BancoInvalido(" ".join(erros.values()))
    banco = BancoCadastrado(normalizar_codigo(codigo), nome.strip(), "manual")
    with conexao:
        conexao.execute(
            "INSERT INTO banco (codigo, ispb, nome, origem) VALUES (?, NULL, ?, 'manual')",
            (banco.codigo, banco.nome),
        )
    return banco
