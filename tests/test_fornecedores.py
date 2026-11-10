import pytest

from econt.dados.banco import BaseDeDados
from econt.dados.contas import DadosConta, cadastrar_conta
from econt.dados.fornecedores import (
    DadosContaFornecedor,
    DadosFornecedor,
    ExclusaoNaoPermitida,
    FornecedorInvalido,
    cadastrar_fornecedor,
    definir_fornecedor_ativo,
    definir_item_ativo,
    editar_fornecedor,
    excluir_fornecedor,
    excluir_item,
    listar_chaves,
    listar_contas_fornecedor,
    listar_fornecedores,
    obter_fornecedor,
    outros_fornecedores_com_a_chave,
    outros_fornecedores_com_a_conta,
    salvar_chave_pix,
    salvar_conta_fornecedor,
)
from econt.dominio.pix import ChaveInvalida

SENHA = "fundo2026saude"
MATERIAIS = DadosFornecedor(
    "pj",
    "11.222.333/0001-81",
    "Distribuidora Exemplo de Materiais Ltda",
    "Exemplo Materiais",
    "(81) 3000-0000",
    "contato@exemplo.com.br",
    "Rua Fictícia, 100 · Recife/PE",
    "Entrega às terças.",
)
MARIA = DadosFornecedor("pf", "529.982.247-25", "Maria Exemplo da Silva")
CONTA_BB = DadosContaFornecedor("001", "1234-5", "98765-4", "corrente")


@pytest.fixture
def base(tmp_path):
    return BaseDeDados.criar(tmp_path / "dados.econt", SENHA)[0]


def _marcar(base, conta_fornecedor_id=None, chave_pix_id=None):
    """Simula uma marcação de cadastro (a tela de marcações chega na v0.5)."""
    entidade = cadastrar_conta(base.conexao, DadosConta("Conta Movimento", "001", "1", "1-1"))
    base.conexao.execute(
        "INSERT INTO marcacao (conta_entidade_id, conta_fornecedor_id, chave_pix_id, criado_em)"
        " VALUES (?, ?, ?, '2026-11-08T10:00:00')",
        (entidade, conta_fornecedor_id, chave_pix_id),
    )


def test_cadastra_com_todos_os_dados(base):
    fornecedor = obter_fornecedor(base.conexao, cadastrar_fornecedor(base.conexao, MATERIAIS))
    assert fornecedor.documento == "11222333000181"
    assert fornecedor.documento_formatado == "11.222.333/0001-81"
    assert fornecedor.nome_fantasia == "Exemplo Materiais"
    assert fornecedor.endereco == "Rua Fictícia, 100 · Recife/PE"
    assert fornecedor.ativo and fornecedor.criado_em and fornecedor.alterado_em


def test_pessoa_fisica_com_cpf(base):
    fornecedor = obter_fornecedor(base.conexao, cadastrar_fornecedor(base.conexao, MARIA))
    assert fornecedor.documento_formatado == "529.982.247-25"
    assert fornecedor.nome_do_documento == "CPF"


@pytest.mark.parametrize(
    "dados, mensagem",
    [
        (DadosFornecedor("pj", "11.222.333/0001-80", "X"), "CNPJ inválido"),
        (DadosFornecedor("pf", "529.982.247-24", "X"), "CPF inválido"),
        (DadosFornecedor("pf", "11.222.333/0001-81", "X"), "O CPF tem só números|11 números"),
        (DadosFornecedor("pj", "11.222.333/0001-81", " "), "razão social"),
        (DadosFornecedor("pj", "11.222.333/0001-81", "X", email="contato@"), "E-mail"),
    ],
)
def test_dados_errados_sao_recusados(base, dados, mensagem):
    with pytest.raises(FornecedorInvalido, match=mensagem):
        cadastrar_fornecedor(base.conexao, dados)


def test_nao_aceita_dois_fornecedores_com_o_mesmo_documento(base):
    cadastrar_fornecedor(base.conexao, MATERIAIS)
    with pytest.raises(FornecedorInvalido, match="já é de Distribuidora Exemplo"):
        cadastrar_fornecedor(base.conexao, DadosFornecedor("pj", "11222333000181", "Outra"))


def test_editar(base):
    fornecedor_id = cadastrar_fornecedor(base.conexao, MATERIAIS)
    dados = obter_fornecedor(base.conexao, fornecedor_id).dados()
    dados.observacoes = "Entrega às quintas."
    editar_fornecedor(base.conexao, fornecedor_id, dados)
    assert obter_fornecedor(base.conexao, fornecedor_id).observacoes == "Entrega às quintas."


def test_busca_por_nome_e_documento(base):
    cadastrar_fornecedor(base.conexao, MATERIAIS)
    cadastrar_fornecedor(base.conexao, MARIA)
    assert [f.razao_social for f in listar_fornecedores(base.conexao, "maria")] == [
        "Maria Exemplo da Silva"
    ]
    assert len(listar_fornecedores(base.conexao, "11.222.333")) == 1
    assert len(listar_fornecedores(base.conexao, "52998224725")) == 1
    assert len(listar_fornecedores(base.conexao, "exemplo materiais")) == 1
    assert len(listar_fornecedores(base.conexao)) == 2


def test_inativo_so_aparece_quando_pedido(base):
    fornecedor_id = cadastrar_fornecedor(base.conexao, MATERIAIS)
    definir_fornecedor_ativo(base.conexao, fornecedor_id, False)
    assert listar_fornecedores(base.conexao) == []
    assert len(listar_fornecedores(base.conexao, incluir_inativos=True)) == 1


def test_excluir_sem_historico(base):
    fornecedor_id = cadastrar_fornecedor(base.conexao, MATERIAIS)
    salvar_conta_fornecedor(base.conexao, fornecedor_id, CONTA_BB)
    salvar_chave_pix(base.conexao, fornecedor_id, "cnpj", "11.222.333/0001-81")
    excluir_fornecedor(base.conexao, fornecedor_id)
    assert listar_fornecedores(base.conexao, incluir_inativos=True) == []
    assert base.conexao.execute("SELECT count(*) FROM conta_fornecedor").fetchone()[0] == 0


def test_com_historico_so_inativa(base):
    fornecedor_id = cadastrar_fornecedor(base.conexao, MATERIAIS)
    conta_id = salvar_conta_fornecedor(base.conexao, fornecedor_id, CONTA_BB)
    _marcar(base, conta_fornecedor_id=conta_id)
    with pytest.raises(ExclusaoNaoPermitida, match="Inative"):
        excluir_fornecedor(base.conexao, fornecedor_id)
    with pytest.raises(ExclusaoNaoPermitida):
        excluir_item(base.conexao, "conta_fornecedor", conta_id)
    definir_fornecedor_ativo(base.conexao, fornecedor_id, False)
    assert base.conexao.execute("SELECT count(*) FROM marcacao").fetchone()[0] == 1


def test_conta_bancaria_do_fornecedor(base):
    fornecedor_id = cadastrar_fornecedor(base.conexao, MATERIAIS)
    salvar_conta_fornecedor(base.conexao, fornecedor_id, CONTA_BB)
    salvar_conta_fornecedor(
        base.conexao, fornecedor_id, DadosContaFornecedor("104", "0456", "00012345-6", "poupanca")
    )
    contas = listar_contas_fornecedor(base.conexao, fornecedor_id)
    assert [(c.banco_rotulo, c.agencia, c.conta, c.nome_do_tipo) for c in contas] == [
        ("001 · Banco do Brasil S.A.", "1234-5", "98765-4", "Conta corrente"),
        ("104 · CAIXA ECONOMICA FEDERAL", "0456", "00012345-6", "Poupança"),
    ]
    assert obter_fornecedor(base.conexao, fornecedor_id).contas_e_chaves == 2


@pytest.mark.parametrize(
    "dados, mensagem",
    [
        (DadosContaFornecedor("", "1234", "1-1"), "banco"),
        (DadosContaFornecedor("001", "", "1-1"), "agência"),
        (DadosContaFornecedor("001", "1234", "11"), "dígito"),
        (DadosContaFornecedor("001", "1234", "1-1", "investimento"), "tipo"),
    ],
)
def test_conta_com_dado_errado(base, dados, mensagem):
    fornecedor_id = cadastrar_fornecedor(base.conexao, MATERIAIS)
    with pytest.raises(FornecedorInvalido, match=mensagem):
        salvar_conta_fornecedor(base.conexao, fornecedor_id, dados)


def test_a_conta_e_do_proprio_fornecedor(base):
    """RN10: a conta fica presa ao fornecedor e não tem titular diferente."""
    colunas = {c[1] for c in base.conexao.execute("PRAGMA table_info(conta_fornecedor)")}
    assert "fornecedor_id" in colunas
    assert not colunas & {"titular", "documento_titular", "cpf_titular"}


def test_mesma_conta_repetida_e_avisada(base):
    a = cadastrar_fornecedor(base.conexao, MATERIAIS)
    b = cadastrar_fornecedor(base.conexao, MARIA)
    salvar_conta_fornecedor(base.conexao, a, CONTA_BB)
    with pytest.raises(FornecedorInvalido, match="já está cadastrada neste fornecedor"):
        salvar_conta_fornecedor(base.conexao, a, CONTA_BB)
    assert outros_fornecedores_com_a_conta(base.conexao, b, CONTA_BB) == [
        "Distribuidora Exemplo de Materiais Ltda"
    ]
    assert outros_fornecedores_com_a_conta(base.conexao, a, CONTA_BB) == []


def test_chaves_pix_dos_cinco_tipos(base):
    fornecedor_id = cadastrar_fornecedor(base.conexao, MATERIAIS)
    salvar_chave_pix(base.conexao, fornecedor_id, "cnpj", "11.222.333/0001-81")
    salvar_chave_pix(base.conexao, fornecedor_id, "email", "financeiro@exemplo.com.br")
    salvar_chave_pix(base.conexao, fornecedor_id, "telefone", "(81) 99999-0000")
    salvar_chave_pix(
        base.conexao, fornecedor_id, "aleatoria", "1a2b3c4d-1a2b-4a2b-8a2b-1a2b3c4d5e6f"
    )
    maria = cadastrar_fornecedor(base.conexao, MARIA)
    salvar_chave_pix(base.conexao, maria, "cpf", "529.982.247-25")
    assert [c.chave_formatada for c in listar_chaves(base.conexao, fornecedor_id)] == [
        "11.222.333/0001-81",
        "financeiro@exemplo.com.br",
        "(81) 99999-0000",
        "1a2b3c4d-1a2b-4a2b-8a2b-1a2b3c4d5e6f",
    ]


def test_chave_de_documento_e_do_proprio_fornecedor(base):
    fornecedor_id = cadastrar_fornecedor(base.conexao, MATERIAIS)
    with pytest.raises(ChaveInvalida, match="próprio fornecedor"):
        salvar_chave_pix(base.conexao, fornecedor_id, "cnpj", "12.ABC.345/01DE-35")
    with pytest.raises(ChaveInvalida, match="pessoa jurídica"):
        salvar_chave_pix(base.conexao, fornecedor_id, "cpf", "529.982.247-25")


def test_mesma_chave_repetida_e_avisada(base):
    a = cadastrar_fornecedor(base.conexao, MATERIAIS)
    b = cadastrar_fornecedor(base.conexao, MARIA)
    salvar_chave_pix(base.conexao, a, "email", "financeiro@exemplo.com.br")
    with pytest.raises(ChaveInvalida, match="já está cadastrada neste fornecedor"):
        salvar_chave_pix(base.conexao, a, "email", "FINANCEIRO@exemplo.com.br")
    assert outros_fornecedores_com_a_chave(base.conexao, b, "email", "Financeiro@Exemplo.com.br")


def test_trocar_documento_com_chave_antiga_e_recusado(base):
    fornecedor_id = cadastrar_fornecedor(base.conexao, MATERIAIS)
    salvar_chave_pix(base.conexao, fornecedor_id, "cnpj", "11.222.333/0001-81")
    dados = obter_fornecedor(base.conexao, fornecedor_id).dados()
    dados.documento = "12.ABC.345/01DE-35"
    with pytest.raises(FornecedorInvalido, match="documento anterior"):
        editar_fornecedor(base.conexao, fornecedor_id, dados)


def test_conta_e_chave_inativas_guardam_marcacoes(base):
    fornecedor_id = cadastrar_fornecedor(base.conexao, MATERIAIS)
    chave_id = salvar_chave_pix(base.conexao, fornecedor_id, "email", "a@exemplo.com.br")
    _marcar(base, chave_pix_id=chave_id)
    definir_item_ativo(base.conexao, "chave_pix", chave_id, False)
    assert not listar_chaves(base.conexao, fornecedor_id)[0].ativa
    definir_item_ativo(base.conexao, "chave_pix", chave_id, True)
    assert listar_chaves(base.conexao, fornecedor_id)[0].ativa
    assert base.conexao.execute("SELECT count(*) FROM marcacao").fetchone()[0] == 1
    with pytest.raises(ValueError):
        definir_item_ativo(base.conexao, "fornecedor; DROP TABLE x", 1, True)
