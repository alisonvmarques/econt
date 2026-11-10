"""Contas da entidade, de onde saem os pagamentos (RF17), e os limites de cada uma (RF18)."""

from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime

from econt.dados.lista_bancos import obter_banco
from econt.dominio.limites import (
    LIMITE_PADRAO,
    Pedido,
    PedidoInvalido,
    SituacaoDoLimite,
    situacao_do_limite,
    validar_pedido,
)

FORMATO_AGENCIA = re.compile(r"\d{1,5}(-[\dXx])?")
FORMATO_CONTA = re.compile(r"\d{1,13}-[\dXx]")


class ContaInvalida(ValueError):
    pass


@dataclass
class DadosConta:
    """O que se digita no formulário da conta."""

    descricao: str
    banco: str
    agencia: str
    conta: str


@dataclass
class ContaEntidade:
    id: int
    descricao: str
    banco: str
    banco_nome: str
    agencia: str
    conta: str
    ativa: bool
    pix: SituacaoDoLimite
    transacao: SituacaoDoLimite

    @property
    def resumo(self) -> str:
        return f"{self.banco} · Ag. {self.agencia} · C/C {self.conta}"

    @property
    def limites(self) -> list[SituacaoDoLimite]:
        return [self.pix, self.transacao]

    def dados(self) -> DadosConta:
        return DadosConta(self.descricao, self.banco, self.agencia, self.conta)


def _agora() -> datetime:
    return datetime.now().replace(microsecond=0)


def _limpar(texto: str) -> str:
    return re.sub(r"\s", "", texto).upper()


def problemas_da_conta(
    conexao: sqlite3.Connection, dados: DadosConta, ignorar_id: int | None = None
) -> dict[str, str]:
    """Erros por campo, em português. Vazio quando está tudo certo."""
    erros = {}
    agencia, conta = _limpar(dados.agencia), _limpar(dados.conta)
    if not dados.descricao.strip():
        erros["descricao"] = "Informe uma descrição, como Conta Movimento."
    if not dados.banco:
        erros["banco"] = "Escolha o banco."
    elif obter_banco(conexao, dados.banco) is None:
        erros["banco"] = "Banco não encontrado. Escolha um banco da lista."
    if not agencia:
        erros["agencia"] = "Informe a agência."
    elif not FORMATO_AGENCIA.fullmatch(agencia):
        erros["agencia"] = "Agência com até 5 números e o dígito, se houver, assim: 1234-5."
    if not conta:
        erros["conta"] = "Informe a conta com o dígito."
    elif not FORMATO_CONTA.fullmatch(conta):
        erros["conta"] = "Informe a conta com o dígito depois do traço, assim: 77777-3."
    if not erros:
        repetida = conexao.execute(
            "SELECT descricao FROM conta_entidade WHERE banco = ? AND agencia = ? AND conta = ?"
            " AND id IS NOT ?",
            (dados.banco, agencia, conta, ignorar_id),
        ).fetchone()
        if repetida:
            erros["conta"] = f"Esta conta já está cadastrada como {repetida[0]}."
    return erros


def _validar(conexao: sqlite3.Connection, dados: DadosConta, ignorar_id: int | None = None):
    erros = problemas_da_conta(conexao, dados, ignorar_id)
    if erros:
        raise ContaInvalida(" ".join(erros.values()))
    return dados.descricao.strip(), dados.banco, _limpar(dados.agencia), _limpar(dados.conta)


def cadastrar_conta(conexao: sqlite3.Connection, dados: DadosConta) -> int:
    """Conta nova começa valendo com R$ 10.000,00 nos dois limites, sem prazo (RN07)."""
    valores = _validar(conexao, dados)
    agora = _agora().isoformat()
    with conexao:
        cursor = conexao.execute(
            """
            INSERT INTO conta_entidade (descricao, banco, agencia, conta, limite_pix,
                limite_transacao, criado_em, alterado_em)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (*valores, LIMITE_PADRAO, LIMITE_PADRAO, agora, agora),
        )
    return cursor.lastrowid


def editar_conta(conexao: sqlite3.Connection, conta_id: int, dados: DadosConta) -> None:
    valores = _validar(conexao, dados, ignorar_id=conta_id)
    with conexao:
        conexao.execute(
            """
            UPDATE conta_entidade SET descricao = ?, banco = ?, agencia = ?, conta = ?,
                alterado_em = ?
            WHERE id = ?
            """,
            (*valores, _agora().isoformat(), conta_id),
        )


def definir_ativa(conexao: sqlite3.Connection, conta_id: int, ativa: bool) -> None:
    """Inativar não apaga nada: limites, pedidos e marcações continuam guardados e voltam
    como estavam na reativação (RN12)."""
    with conexao:
        conexao.execute(
            "UPDATE conta_entidade SET ativa = ?, alterado_em = ? WHERE id = ?",
            (int(ativa), _agora().isoformat(), conta_id),
        )


def _pedidos(conexao: sqlite3.Connection, conta_id: int) -> list[Pedido]:
    linhas = conexao.execute(
        "SELECT tipo, valor, pedido_em FROM pedido_limite WHERE conta_id = ?", (conta_id,)
    ).fetchall()
    return [Pedido(tipo, valor, datetime.fromisoformat(em)) for tipo, valor, em in linhas]


def _montar(conexao: sqlite3.Connection, linha: tuple, agora: datetime) -> ContaEntidade:
    conta_id, descricao, banco, banco_nome, agencia, conta, ativa, pix, transacao = linha
    pedidos = _pedidos(conexao, conta_id)
    return ContaEntidade(
        conta_id,
        descricao,
        banco,
        banco_nome,
        agencia,
        conta,
        bool(ativa),
        situacao_do_limite("pix", pix, pedidos, agora),
        situacao_do_limite("transacao", transacao, pedidos, agora),
    )


_SELECAO = """
    SELECT c.id, c.descricao, c.banco, b.nome, c.agencia, c.conta, c.ativa,
        c.limite_pix, c.limite_transacao
    FROM conta_entidade c JOIN banco b ON b.codigo = c.banco
"""


def listar_contas(
    conexao: sqlite3.Connection, agora: datetime | None = None
) -> list[ContaEntidade]:
    """Ativas primeiro, depois em ordem de descrição."""
    agora = agora or _agora()
    linhas = conexao.execute(
        _SELECAO + " ORDER BY c.ativa DESC, c.descricao COLLATE NOCASE"
    ).fetchall()
    return [_montar(conexao, linha, agora) for linha in linhas]


def obter_conta(
    conexao: sqlite3.Connection, conta_id: int, agora: datetime | None = None
) -> ContaEntidade:
    linha = conexao.execute(_SELECAO + " WHERE c.id = ?", (conta_id,)).fetchone()
    if linha is None:
        raise ContaInvalida("Conta não encontrada.")
    return _montar(conexao, linha, agora or _agora())


def registrar_pedido(
    conexao: sqlite3.Connection,
    conta_id: int,
    tipo: str,
    valor: int,
    pedido_em: datetime,
    agora: datetime | None = None,
) -> Pedido:
    """RN11: o novo valor só passa a valer 24 horas depois do pedido."""
    agora = agora or _agora()
    conta = obter_conta(conexao, conta_id, agora)
    if not conta.ativa:
        raise PedidoInvalido("A conta está inativa. Reative a conta para registrar o pedido.")
    situacao = {"pix": conta.pix, "transacao": conta.transacao}.get(tipo)
    if situacao is None:
        raise PedidoInvalido("Escolha o limite: Pix ou transação.")
    pedido_em = pedido_em.replace(second=0, microsecond=0)
    validar_pedido(situacao, valor, pedido_em, agora)
    with conexao:
        conexao.execute(
            "INSERT INTO pedido_limite (conta_id, tipo, valor, pedido_em, criado_em)"
            " VALUES (?, ?, ?, ?, ?)",
            (conta_id, tipo, valor, pedido_em.isoformat(), agora.isoformat()),
        )
    return Pedido(tipo, valor, pedido_em)
