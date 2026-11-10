"""Consulta: buscar o fornecedor e ver onde cada conta e chave está cadastrada (RF02 a RF04)."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from econt.dados.contas import ContaEntidade, listar_contas
from econt.dados.fornecedores import Fornecedor, listar_fornecedores, obter_fornecedor
from econt.dados.marcacoes import CadastroVigente, cadastros_vigentes
from econt.dominio.documentos import somente_caracteres
from econt.dominio.texto import encontrar


@dataclass
class Encontrado:
    fornecedor: Fornecedor
    campo: str  # "razao_social", "nome_fantasia" ou "documento"
    trecho: tuple[int, int]
    contas: int
    chaves: int

    @property
    def resumo(self) -> str:
        contas = f"{self.contas} conta" + ("s" if self.contas != 1 else "")
        chaves = f"{self.chaves} chave" + ("s" if self.chaves != 1 else "") + " Pix"
        return f"{contas} · {chaves}"


def _quantos_ativos(conexao: sqlite3.Connection) -> dict[int, tuple[int, int]]:
    contas = dict(
        conexao.execute(
            "SELECT fornecedor_id, count(*) FROM conta_fornecedor WHERE ativa = 1"
            " GROUP BY fornecedor_id"
        ).fetchall()
    )
    chaves = dict(
        conexao.execute(
            "SELECT fornecedor_id, count(*) FROM chave_pix WHERE ativa = 1 GROUP BY fornecedor_id"
        ).fetchall()
    )
    return {i: (contas.get(i, 0), chaves.get(i, 0)) for i in set(contas) | set(chaves)}


def buscar(conexao: sqlite3.Connection, termo: str) -> list[Encontrado]:
    """Só fornecedores ativos (RN04). Procura na razão social, no nome fantasia e no
    CNPJ/CPF, sem diferenciar maiúsculas e acentos. Quem começa com o termo vem primeiro."""
    if not termo.strip():
        return []
    documento = somente_caracteres(termo)
    quantos = _quantos_ativos(conexao)
    encontrados = []
    for f in listar_fornecedores(conexao):
        campo, trecho = None, None
        for nome in ("razao_social", "nome_fantasia"):
            if posicao := encontrar(getattr(f, nome), termo):
                campo, trecho = nome, posicao
                break
        if campo is None and len(documento) >= 2 and documento in f.documento:
            campo = "documento"
            inicio = f.documento.index(documento)
            trecho = (inicio, inicio + len(documento))
        if campo:
            contas, chaves = quantos.get(f.id, (0, 0))
            encontrados.append(Encontrado(f, campo, trecho, contas, chaves))
    encontrados.sort(key=lambda e: (e.trecho[0] != 0, e.fornecedor.razao_social.lower()))
    return encontrados


@dataclass
class ResultadoConsulta:
    """O que a Consulta mostra e a meia folha imprime: só o que está ativo (RNF11)."""

    fornecedor: Fornecedor
    contas_entidade: list[ContaEntidade]
    cadastros: list[CadastroVigente]

    @property
    def sem_cadastro(self) -> list[CadastroVigente]:
        return [c for c in self.cadastros if c.sem_cadastro]

    def cadastrada(self, cadastro: CadastroVigente, conta: ContaEntidade) -> bool:
        return any(c.id == conta.id for c in cadastro.contas_entidade)


class FornecedorInativo(ValueError):
    pass


def consultar(conexao: sqlite3.Connection, fornecedor_id: int) -> ResultadoConsulta:
    fornecedor = obter_fornecedor(conexao, fornecedor_id)
    if not fornecedor.ativo:
        raise FornecedorInativo("Fornecedor inativo não aparece na Consulta.")
    contas = [c for c in listar_contas(conexao) if c.ativa]
    contas.sort(key=lambda c: c.id)
    return ResultadoConsulta(fornecedor, contas, cadastros_vigentes(conexao, fornecedor_id))
