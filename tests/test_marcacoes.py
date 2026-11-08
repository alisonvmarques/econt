import pytest

from baliza.dados.banco import BaseDeDados
from baliza.dados.contas import DadosConta, cadastrar_conta, definir_ativa
from baliza.dados.fornecedores import (
    DadosContaFornecedor,
    DadosFornecedor,
    ExclusaoNaoPermitida,
    cadastrar_fornecedor,
    definir_fornecedor_ativo,
    definir_item_ativo,
    excluir_fornecedor,
    salvar_chave_pix,
    salvar_conta_fornecedor,
    tem_historico,
)
from baliza.dados.marcacoes import (
    MarcacaoInvalida,
    cadastros_vigentes,
    definir_marcacao,
    itens_do_fornecedor,
    marcacoes_do_item,
    marcado,
    marcar_todas,
)

SENHA = "fundo2026saude"


@pytest.fixture
def cenario(tmp_path):
    base = BaseDeDados.criar(tmp_path / "dados.baliza", SENHA)[0]
    c = base.conexao
    entidade = {
        nome: cadastrar_conta(c, DadosConta(nome, "001", "1234-5", conta))
        for nome, conta in (
            ("Conta Movimento", "55555-0"),
            ("Conta Saúde", "77777-1"),
            ("Conta Pix", "66666-2"),
        )
    }
    f = cadastrar_fornecedor(
        c, DadosFornecedor("pj", "11.222.333/0001-81", "Distribuidora Exemplo de Materiais Ltda")
    )
    salvar_conta_fornecedor(c, f, DadosContaFornecedor("001", "1234-5", "98765-4"))
    salvar_chave_pix(c, f, "cnpj", "11.222.333/0001-81")
    conta, chave = itens_do_fornecedor(c, f)
    return base, entidade, f, conta, chave


def _vigentes(base, f):
    return {
        v.item.rotulo: [c.descricao for c in v.contas_entidade]
        for v in cadastros_vigentes(base.conexao, f)
    }


def test_uma_linha_para_cada_conta_e_chave(cenario):
    base, _, f, conta, chave = cenario
    assert [i.rotulo for i in itens_do_fornecedor(base.conexao, f)] == [
        "001 · Ag. 1234-5 · C/C 98765-4",
        "Pix · 11.222.333/0001-81",
    ]


def test_marcar_e_desmarcar(cenario):
    base, entidade, f, conta, chave = cenario
    definir_marcacao(base.conexao, conta, entidade["Conta Movimento"], True)
    assert marcado(base.conexao, conta, entidade["Conta Movimento"])
    assert not marcado(base.conexao, conta, entidade["Conta Saúde"])
    assert not marcado(base.conexao, chave, entidade["Conta Movimento"])
    definir_marcacao(base.conexao, conta, entidade["Conta Movimento"], False)
    assert not marcado(base.conexao, conta, entidade["Conta Movimento"])
    definir_marcacao(base.conexao, conta, entidade["Conta Movimento"], True)
    assert base.conexao.execute("SELECT count(*) FROM marcacao").fetchone()[0] == 1


def test_desmarcar_guarda_o_historico(cenario):
    base, entidade, f, conta, _ = cenario
    definir_marcacao(base.conexao, conta, entidade["Conta Movimento"], True)
    definir_marcacao(base.conexao, conta, entidade["Conta Movimento"], False)
    assert tem_historico(base.conexao, f)
    with pytest.raises(ExclusaoNaoPermitida):
        excluir_fornecedor(base.conexao, f)


def test_marcar_todas_usa_as_contas_ativas_da_entidade(cenario):
    base, entidade, f, _, chave = cenario
    definir_ativa(base.conexao, entidade["Conta Pix"], False)
    assert marcar_todas(base.conexao, chave) == 2
    assert marcacoes_do_item(base.conexao, chave) == {
        entidade["Conta Movimento"],
        entidade["Conta Saúde"],
    }


def test_conta_sem_cadastro_fica_evidente(cenario):
    base, entidade, f, conta, chave = cenario
    definir_marcacao(base.conexao, chave, entidade["Conta Saúde"], True)
    vigentes = cadastros_vigentes(base.conexao, f)
    assert [v.sem_cadastro for v in vigentes] == [True, False]


def test_conta_da_entidade_inativa_guarda_as_marcacoes(cenario):
    """RN12, caso 1."""
    base, entidade, f, conta, _ = cenario
    marcar_todas(base.conexao, conta)
    definir_ativa(base.conexao, entidade["Conta Saúde"], False)
    assert _vigentes(base, f)["001 · Ag. 1234-5 · C/C 98765-4"] == ["Conta Movimento", "Conta Pix"]
    definir_ativa(base.conexao, entidade["Conta Saúde"], True)
    assert _vigentes(base, f)["001 · Ag. 1234-5 · C/C 98765-4"] == [
        "Conta Movimento",
        "Conta Saúde",
        "Conta Pix",
    ]


def test_fornecedor_inativo_guarda_as_marcacoes(cenario):
    """RN12, caso 2."""
    base, entidade, f, conta, chave = cenario
    marcar_todas(base.conexao, conta)
    definir_marcacao(base.conexao, chave, entidade["Conta Pix"], True)
    antes = _vigentes(base, f)
    definir_fornecedor_ativo(base.conexao, f, False)
    assert cadastros_vigentes(base.conexao, f) == []
    with pytest.raises(MarcacaoInvalida, match="ativos"):
        definir_marcacao(base.conexao, chave, entidade["Conta Movimento"], True)
    definir_fornecedor_ativo(base.conexao, f, True)
    assert _vigentes(base, f) == antes


def test_conta_ou_chave_do_fornecedor_inativa_guarda_as_marcacoes(cenario):
    """RN12, caso 3."""
    base, entidade, f, conta, chave = cenario
    marcar_todas(base.conexao, chave)
    definir_item_ativo(base.conexao, "chave_pix", chave.id, False)
    assert list(_vigentes(base, f)) == ["001 · Ag. 1234-5 · C/C 98765-4"]
    definir_item_ativo(base.conexao, "chave_pix", chave.id, True)
    assert _vigentes(base, f)["Pix · 11.222.333/0001-81"] == [
        "Conta Movimento",
        "Conta Saúde",
        "Conta Pix",
    ]
