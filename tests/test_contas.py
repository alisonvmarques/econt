from datetime import datetime, timedelta

import pytest

from econt.dados.banco import BaseDeDados
from econt.dados.contas import (
    ContaInvalida,
    DadosConta,
    cadastrar_conta,
    definir_ativa,
    editar_conta,
    listar_contas,
    obter_conta,
    registrar_pedido,
)
from econt.dados.lista_bancos import cadastrar_banco_manual
from econt.dominio.limites import PedidoInvalido

SENHA = "fundo2026saude"
AGORA = datetime(2026, 11, 8, 10, 15)
MOVIMENTO = DadosConta("Conta Movimento", "001", "1234-5", "55555-0")


@pytest.fixture
def base(tmp_path):
    return BaseDeDados.criar(tmp_path / "dados.econt", SENHA)[0]


def test_conta_nova_comeca_com_dez_mil_nos_dois_limites(base):
    conta = obter_conta(base.conexao, cadastrar_conta(base.conexao, MOVIMENTO), AGORA)
    assert conta.resumo == "001 · Ag. 1234-5 · C/C 55555-0"
    assert conta.banco_nome == "Banco do Brasil S.A."
    assert conta.pix.vale_agora == conta.transacao.vale_agora == 1_000_000
    assert conta.pix.em_liberacao is None and conta.transacao.em_liberacao is None
    assert conta.ativa


@pytest.mark.parametrize(
    "dados, campo",
    [
        (DadosConta("", "001", "1234-5", "55555-0"), "descrição"),
        (DadosConta("Conta", "", "1234-5", "55555-0"), "banco"),
        (DadosConta("Conta", "998877", "1234-5", "55555-0"), "Banco não encontrado"),
        (DadosConta("Conta", "001", "12a4", "55555-0"), "Agência"),
        (DadosConta("Conta", "001", "1234", "555550"), "dígito depois do traço"),
    ],
)
def test_conta_com_dado_errado_nao_e_salva(base, dados, campo):
    with pytest.raises(ContaInvalida, match=campo):
        cadastrar_conta(base.conexao, dados)


def test_mesma_conta_nao_e_cadastrada_duas_vezes(base):
    cadastrar_conta(base.conexao, MOVIMENTO)
    with pytest.raises(ContaInvalida, match="já está cadastrada como Conta Movimento"):
        cadastrar_conta(base.conexao, DadosConta("Outra", "001", "1234-5", "55555-0"))


def test_editar_conta(base):
    conta_id = cadastrar_conta(base.conexao, MOVIMENTO)
    editar_conta(base.conexao, conta_id, DadosConta("Conta Saúde", "104", "0456", "00077777-1"))
    conta = obter_conta(base.conexao, conta_id)
    assert (conta.descricao, conta.resumo) == ("Conta Saúde", "104 · Ag. 0456 · C/C 00077777-1")
    editar_conta(base.conexao, conta_id, DadosConta("Conta Saúde", "104", "0456", "00077777-1"))


def test_inativar_e_reativar_guarda_tudo_como_estava(base):
    conta_id = cadastrar_conta(base.conexao, MOVIMENTO)
    registrar_pedido(base.conexao, conta_id, "pix", 3_000_000, AGORA, AGORA)
    definir_ativa(base.conexao, conta_id, False)
    inativa = obter_conta(base.conexao, conta_id, AGORA)
    assert not inativa.ativa
    with pytest.raises(PedidoInvalido, match="inativa"):
        registrar_pedido(base.conexao, conta_id, "transacao", 2_000_000, AGORA, AGORA)
    definir_ativa(base.conexao, conta_id, True)
    reativada = obter_conta(base.conexao, conta_id, AGORA)
    assert reativada.ativa
    assert reativada.pix.em_liberacao.valor == 3_000_000


def test_lista_mostra_ativas_primeiro(base):
    cadastrar_conta(base.conexao, DadosConta("Conta A", "001", "1", "1-1"))
    b = cadastrar_conta(base.conexao, DadosConta("Conta B", "001", "1", "2-2"))
    cadastrar_conta(base.conexao, DadosConta("Conta C", "001", "1", "3-3"))
    definir_ativa(base.conexao, b, False)
    assert [c.descricao for c in listar_contas(base.conexao)] == ["Conta A", "Conta C", "Conta B"]


def test_pedido_fica_em_liberacao_por_24_horas(base):
    conta_id = cadastrar_conta(base.conexao, MOVIMENTO)
    registrar_pedido(base.conexao, conta_id, "transacao", 2_500_000, AGORA, AGORA)
    durante = obter_conta(base.conexao, conta_id, AGORA + timedelta(hours=23))
    assert durante.transacao.vale_agora == 1_000_000
    assert durante.transacao.em_liberacao.liberado_em == datetime(2026, 11, 9, 10, 15)
    assert durante.pix.em_liberacao is None
    depois = obter_conta(base.conexao, conta_id, AGORA + timedelta(hours=24))
    assert depois.transacao.vale_agora == 2_500_000


def test_limites_sao_de_cada_conta_da_entidade(base):
    """RN06: os pedidos ficam presos à conta da entidade; outra conta não é afetada."""
    movimento = cadastrar_conta(base.conexao, MOVIMENTO)
    pix = cadastrar_conta(base.conexao, DadosConta("Conta Pix", "001", "1234-5", "66666-2"))
    registrar_pedido(base.conexao, movimento, "pix", 3_000_000, AGORA, AGORA)
    depois = AGORA + timedelta(days=1)
    assert obter_conta(base.conexao, movimento, depois).pix.vale_agora == 3_000_000
    assert obter_conta(base.conexao, pix, depois).pix.vale_agora == 1_000_000
    colunas = {c[1] for c in base.conexao.execute("PRAGMA table_info(pedido_limite)")}
    assert "fornecedor_id" not in colunas


def test_contas_e_pedidos_sobrevivem_a_reabertura(tmp_path):
    caminho = tmp_path / "dados.econt"
    base = BaseDeDados.criar(caminho, SENHA)[0]
    conta_id = cadastrar_conta(base.conexao, MOVIMENTO)
    registrar_pedido(base.conexao, conta_id, "pix", 3_000_000, AGORA, AGORA)
    base.fechar()
    reaberta = BaseDeDados.abrir(caminho, senha=SENHA)
    assert obter_conta(reaberta.conexao, conta_id, AGORA).pix.em_liberacao.valor == 3_000_000


def test_conta_em_banco_cadastrado_manualmente(base):
    cadastrar_banco_manual(base.conexao, "999", "Banco Fictício Cooperativo")
    conta_id = cadastrar_conta(base.conexao, DadosConta("Conta Coop", "999", "1", "10-1"))
    assert obter_conta(base.conexao, conta_id).banco_nome == "Banco Fictício Cooperativo"
