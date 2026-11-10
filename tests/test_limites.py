from datetime import datetime, timedelta

import pytest

from econt.dominio.limites import (
    LIMITE_PADRAO,
    Pedido,
    PedidoInvalido,
    situacao_do_limite,
    validar_pedido,
)

PEDIDO_EM = datetime(2026, 11, 7, 14, 30)


def test_sem_pedido_vale_o_valor_inicial():
    situacao = situacao_do_limite("pix", LIMITE_PADRAO, [], PEDIDO_EM)
    assert situacao.vale_agora == 1_000_000
    assert situacao.em_liberacao is None


def test_durante_24_horas_vale_o_atual_e_o_novo_fica_em_liberacao():
    pedidos = [Pedido("pix", 3_000_000, PEDIDO_EM)]
    um_minuto_antes = PEDIDO_EM + timedelta(hours=23, minutes=59)
    situacao = situacao_do_limite("pix", LIMITE_PADRAO, pedidos, um_minuto_antes)
    assert situacao.vale_agora == LIMITE_PADRAO
    assert situacao.em_liberacao.valor == 3_000_000
    assert situacao.em_liberacao.liberado_em == datetime(2026, 11, 8, 14, 30)


def test_depois_de_24_horas_o_novo_valor_passa_a_valer():
    pedidos = [Pedido("pix", 3_000_000, PEDIDO_EM)]
    situacao = situacao_do_limite("pix", LIMITE_PADRAO, pedidos, PEDIDO_EM + timedelta(hours=24))
    assert situacao.vale_agora == 3_000_000
    assert situacao.em_liberacao is None


def test_reducao_tambem_espera_24_horas():
    pedidos = [Pedido("transacao", 500_000, PEDIDO_EM)]
    situacao = situacao_do_limite("transacao", LIMITE_PADRAO, pedidos, PEDIDO_EM)
    assert situacao.vale_agora == LIMITE_PADRAO
    assert situacao.em_liberacao.valor == 500_000


def test_cada_limite_tem_seus_proprios_pedidos():
    pedidos = [Pedido("pix", 3_000_000, PEDIDO_EM)]
    depois = PEDIDO_EM + timedelta(days=2)
    assert situacao_do_limite("pix", LIMITE_PADRAO, pedidos, depois).vale_agora == 3_000_000
    assert situacao_do_limite("transacao", LIMITE_PADRAO, pedidos, depois).vale_agora == (
        LIMITE_PADRAO
    )


def test_vale_o_pedido_liberado_mais_recente():
    pedidos = [
        Pedido("pix", 2_000_000, PEDIDO_EM),
        Pedido("pix", 4_000_000, PEDIDO_EM + timedelta(days=3)),
        Pedido("pix", 1_500_000, PEDIDO_EM + timedelta(days=5)),
    ]
    situacao = situacao_do_limite("pix", LIMITE_PADRAO, pedidos, PEDIDO_EM + timedelta(days=5))
    assert situacao.vale_agora == 4_000_000
    assert situacao.em_liberacao.valor == 1_500_000


def test_pedido_no_futuro_ou_igual_ao_atual_e_recusado():
    situacao = situacao_do_limite("pix", LIMITE_PADRAO, [], PEDIDO_EM)
    with pytest.raises(PedidoInvalido, match="futuro"):
        validar_pedido(situacao, 2_000_000, PEDIDO_EM + timedelta(hours=1), PEDIDO_EM)
    with pytest.raises(PedidoInvalido, match="já é R\\$ 10.000,00"):
        validar_pedido(situacao, LIMITE_PADRAO, PEDIDO_EM, PEDIDO_EM)
    with pytest.raises(PedidoInvalido, match="maior que zero"):
        validar_pedido(situacao, 0, PEDIDO_EM, PEDIDO_EM)
    validar_pedido(situacao, 2_000_000, PEDIDO_EM, PEDIDO_EM)
