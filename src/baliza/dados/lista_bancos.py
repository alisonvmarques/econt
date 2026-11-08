"""Lista oficial de bancos do Banco Central, que vem junto com o Baliza (RN13)."""

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
    texto = resources.files("baliza.dados.recursos").joinpath("bancos.csv").read_text("utf-8")
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
