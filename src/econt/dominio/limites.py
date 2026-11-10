"""Limites diários das contas da entidade e o prazo de 24 horas dos pedidos (RN06, RN07, RN11).

Os limites são por conta da entidade e por dia, nunca por fornecedor (RN06). Toda conta nova
começa com R$ 10.000,00 nos dois limites (RN07). Um pedido de alteração, de aumento ou de
redução, só passa a valer 24 horas depois do pedido; até lá vale o limite atual (RN11).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from econt.dominio.dinheiro import formatar_reais

LIMITE_PADRAO = 1_000_000  # R$ 10.000,00 em centavos
PRAZO_DE_LIBERACAO = timedelta(hours=24)
TIPOS_DE_LIMITE = {"pix": "Pix", "transacao": "Transação"}


class PedidoInvalido(ValueError):
    pass


@dataclass(frozen=True)
class Pedido:
    tipo: str
    valor: int
    pedido_em: datetime

    @property
    def liberado_em(self) -> datetime:
        return self.pedido_em + PRAZO_DE_LIBERACAO


@dataclass(frozen=True)
class SituacaoDoLimite:
    tipo: str
    vale_agora: int
    em_liberacao: Pedido | None

    @property
    def nome(self) -> str:
        return TIPOS_DE_LIMITE[self.tipo]


def situacao_do_limite(
    tipo: str, inicial: int, pedidos: list[Pedido], agora: datetime
) -> SituacaoDoLimite:
    """O valor que vale agora e o pedido que ainda está em liberação, se houver.

    Vale o pedido mais recente que já completou 24 horas; sem nenhum, vale o valor inicial.
    Entre os que ainda não completaram, mostra o mais recente, que é o que vai valer.
    """
    do_tipo = sorted((p for p in pedidos if p.tipo == tipo), key=lambda p: p.pedido_em)
    liberados = [p for p in do_tipo if p.liberado_em <= agora]
    pendentes = [p for p in do_tipo if p.liberado_em > agora]
    vale_agora = liberados[-1].valor if liberados else inicial
    return SituacaoDoLimite(tipo, vale_agora, pendentes[-1] if pendentes else None)


def validar_pedido(
    situacao: SituacaoDoLimite, valor: int, pedido_em: datetime, agora: datetime
) -> None:
    if situacao.tipo not in TIPOS_DE_LIMITE:
        raise PedidoInvalido("Escolha o limite: Pix ou transação.")
    if valor <= 0:
        raise PedidoInvalido("O novo valor precisa ser maior que zero.")
    if pedido_em > agora + timedelta(minutes=1):
        raise PedidoInvalido("A data e hora do pedido não pode estar no futuro.")
    if situacao.em_liberacao and valor == situacao.em_liberacao.valor:
        raise PedidoInvalido(
            f"Já existe um pedido de {formatar_reais(valor)} em liberação no limite "
            f"{situacao.nome}."
        )
    if not situacao.em_liberacao and valor == situacao.vale_agora:
        raise PedidoInvalido(f"O limite {situacao.nome} já é {formatar_reais(valor)}.")


def formatar_data_hora(momento: datetime) -> str:
    return momento.strftime("%d/%m/%Y às %H:%M")
