"""Marcações: em quais contas da entidade cada conta e chave Pix do fornecedor está
cadastrada como favorecido (RF11, RF12, RF13, RN12).

Uma marcação nunca é apagada. Desmarcar guarda a data em que foi desmarcada; marcar de novo
reaproveita a mesma linha. Inativar o fornecedor, a conta ou a chave dele, ou a conta da
entidade, não mexe nas marcações: elas só deixam de valer na Consulta enquanto algo estiver
inativo, e voltam exatamente como estavam na reativação.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime

from baliza.dados.contas import ContaEntidade, listar_contas
from baliza.dados.fornecedores import (
    ChavePix,
    ContaFornecedor,
    listar_chaves,
    listar_contas_fornecedor,
    obter_fornecedor,
)


class MarcacaoInvalida(ValueError):
    pass


@dataclass
class Item:
    """Uma linha da aba Cadastros: uma conta ou uma chave Pix do fornecedor."""

    tipo: str  # "conta" ou "chave"
    id: int
    rotulo: str
    ativo: bool
    nome: str = ""  # "Conta corrente", "Pix · CNPJ"
    dados: str = ""  # "001 · Ag. 1234-5 · C/C 98765-4", a chave formatada

    @property
    def coluna(self) -> str:
        return "conta_fornecedor_id" if self.tipo == "conta" else "chave_pix_id"


def item_da_conta(conta: ContaFornecedor) -> Item:
    dados = f"{conta.banco} · Ag. {conta.agencia} · C/C {conta.conta}"
    return Item("conta", conta.id, dados, conta.ativa, conta.nome_do_tipo, dados)


def item_da_chave(chave: ChavePix) -> Item:
    return Item(
        "chave",
        chave.id,
        f"Pix · {chave.chave_formatada}",
        chave.ativa,
        f"Pix · {chave.nome_do_tipo}",
        chave.chave_formatada,
    )


def itens_do_fornecedor(conexao: sqlite3.Connection, fornecedor_id: int) -> list[Item]:
    contas = [item_da_conta(c) for c in listar_contas_fornecedor(conexao, fornecedor_id)]
    chaves = [item_da_chave(c) for c in listar_chaves(conexao, fornecedor_id)]
    return contas + chaves


def _agora() -> str:
    return datetime.now().replace(microsecond=0).isoformat()


def marcado(conexao: sqlite3.Connection, item: Item, conta_entidade_id: int) -> bool:
    return bool(
        conexao.execute(
            f"SELECT count(*) FROM marcacao WHERE {item.coluna} = ? AND conta_entidade_id = ?"
            " AND desmarcada_em IS NULL",
            (item.id, conta_entidade_id),
        ).fetchone()[0]
    )


def marcacoes_do_item(conexao: sqlite3.Connection, item: Item) -> set[int]:
    """Contas da entidade marcadas para o item, ativas ou não (o que fica guardado)."""
    linhas = conexao.execute(
        f"SELECT conta_entidade_id FROM marcacao WHERE {item.coluna} = ? AND desmarcada_em IS NULL",
        (item.id,),
    ).fetchall()
    return {linha[0] for linha in linhas}


def _conferir_ativos(conexao: sqlite3.Connection, item: Item, conta_entidade_id: int) -> None:
    tabela = "conta_fornecedor" if item.tipo == "conta" else "chave_pix"
    linha = conexao.execute(
        f"SELECT i.ativa, f.ativo FROM {tabela} i JOIN fornecedor f ON f.id = i.fornecedor_id"
        " WHERE i.id = ?",
        (item.id,),
    ).fetchone()
    entidade = conexao.execute(
        "SELECT ativa FROM conta_entidade WHERE id = ?", (conta_entidade_id,)
    ).fetchone()
    if linha is None or entidade is None:
        raise MarcacaoInvalida("Conta ou chave não encontrada.")
    if not (linha[0] and linha[1] and entidade[0]):
        raise MarcacaoInvalida("Só é possível marcar com o fornecedor, a conta e a chave ativos.")


def definir_marcacao(
    conexao: sqlite3.Connection, item: Item, conta_entidade_id: int, marcar: bool
) -> None:
    """Marcada = cadastrada como favorecido nessa conta da entidade; desmarcada = não."""
    _conferir_ativos(conexao, item, conta_entidade_id)
    agora = _agora()
    existente = conexao.execute(
        f"SELECT id FROM marcacao WHERE {item.coluna} = ? AND conta_entidade_id = ?",
        (item.id, conta_entidade_id),
    ).fetchone()
    with conexao:
        if existente:
            conexao.execute(
                "UPDATE marcacao SET desmarcada_em = ? WHERE id = ?",
                (None if marcar else agora, existente[0]),
            )
        elif marcar:
            conexao.execute(
                f"INSERT INTO marcacao (conta_entidade_id, {item.coluna}, criado_em)"
                " VALUES (?, ?, ?)",
                (conta_entidade_id, item.id, agora),
            )


def marcar_todas(conexao: sqlite3.Connection, item: Item) -> int:
    """RF12: marca o item em todas as contas ativas da entidade. Devolve quantas são."""
    contas = [c for c in listar_contas(conexao) if c.ativa]
    for conta in contas:
        definir_marcacao(conexao, item, conta.id, True)
    return len(contas)


@dataclass
class CadastroVigente:
    """O que vale na Consulta para uma conta ou chave do fornecedor."""

    item: Item
    contas_entidade: list[ContaEntidade]

    @property
    def sem_cadastro(self) -> bool:
        return not self.contas_entidade


def cadastros_vigentes(conexao: sqlite3.Connection, fornecedor_id: int) -> list[CadastroVigente]:
    """Para a Consulta: só fornecedor, contas, chaves e contas da entidade ativos (RN04, RN12).

    Um fornecedor inativo não tem nada vigente. Uma conta da entidade inativa some das
    marcações, mas elas continuam guardadas e voltam na reativação.
    """
    if not obter_fornecedor(conexao, fornecedor_id).ativo:
        return []
    ativas = {c.id: c for c in listar_contas(conexao) if c.ativa}
    vigentes = []
    for item in itens_do_fornecedor(conexao, fornecedor_id):
        if not item.ativo:
            continue
        marcadas = [ativas[i] for i in sorted(marcacoes_do_item(conexao, item)) if i in ativas]
        vigentes.append(CadastroVigente(item, marcadas))
    return vigentes
