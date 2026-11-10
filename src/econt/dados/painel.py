"""Painel inicial: o resumo do que está cadastrado e o que pede atenção (RF01)."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from datetime import datetime

from econt.dados.contas import listar_contas
from econt.dados.marcacoes import cadastros_vigentes
from econt.dominio.dinheiro import formatar_reais
from econt.dominio.limites import formatar_data_hora


@dataclass
class Resumo:
    fornecedores_ativos: int
    contas_e_chaves: int
    contas_entidade: int
    limites_em_liberacao: list[str] = field(default_factory=list)
    sem_cadastro: int = 0


def resumir(conexao: sqlite3.Connection, agora: datetime | None = None) -> Resumo:
    """Contas e chaves contam só as ativas de fornecedores ativos: o que vale na Consulta."""
    agora = agora or datetime.now()
    fornecedores = [
        linha[0] for linha in conexao.execute("SELECT id FROM fornecedor WHERE ativo = 1")
    ]
    contas_e_chaves = 0
    sem_cadastro = 0
    for fornecedor_id in fornecedores:
        vigentes = cadastros_vigentes(conexao, fornecedor_id)
        contas_e_chaves += len(vigentes)
        sem_cadastro += sum(1 for v in vigentes if v.sem_cadastro)
    contas = [c for c in listar_contas(conexao, agora) if c.ativa]
    liberacoes = []
    for conta in contas:
        for situacao in conta.limites:
            if pedido := situacao.em_liberacao:
                liberacoes.append(
                    f"O limite {situacao.nome} da {conta.descricao} muda para "
                    f"{formatar_reais(pedido.valor)} em {formatar_data_hora(pedido.liberado_em)}."
                )
    return Resumo(len(fornecedores), contas_e_chaves, len(contas), liberacoes, sem_cadastro)
