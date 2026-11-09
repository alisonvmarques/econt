import pytest

from baliza.dados.banco import BaseDeDados
from baliza.dados.contas import DadosConta, cadastrar_conta, definir_ativa
from baliza.dados.fornecedores import (
    DadosContaFornecedor,
    DadosFornecedor,
    cadastrar_fornecedor,
    definir_fornecedor_ativo,
    salvar_chave_pix,
    salvar_conta_fornecedor,
)
from baliza.dados.marcacoes import itens_do_fornecedor, marcacoes_do_item
from baliza.interface import cadastros as telas
from baliza.interface.fornecedores import PaginaFornecedores

SENHA = "fundo2026saude"


@pytest.fixture
def cenario(tmp_path):
    base = BaseDeDados.criar(tmp_path / "dados.baliza", SENHA)[0]
    c = base.conexao
    contas = [
        cadastrar_conta(c, DadosConta(nome, "001", "1234-5", numero))
        for nome, numero in (("Conta Movimento", "55555-0"), ("Conta Saúde", "77777-1"))
    ]
    f = cadastrar_fornecedor(
        c, DadosFornecedor("pj", "11.222.333/0001-81", "Distribuidora Exemplo de Materiais Ltda")
    )
    salvar_conta_fornecedor(c, f, DadosContaFornecedor("001", "1234-5", "98765-4"))
    salvar_chave_pix(c, f, "email", "financeiro@exemplo.com.br")
    pagina = PaginaFornecedores(base)
    pagina.abrir_ficha(f)
    return base, contas, f, pagina


def test_grade_com_contas_da_entidade_e_itens_do_fornecedor(aplicacao, cenario):
    base, contas, f, pagina = cenario
    painel = pagina.ficha.aba_cadastros
    cabecalho = [painel.tabela.horizontalHeaderItem(i).text() for i in range(4)]
    assert cabecalho == ["Conta ou chave", "Conta Movimento", "Conta Saúde", ""]
    assert painel.tabela.rowCount() == 2
    assert len(painel.botoes_todas) == 2


def test_marcar_salva_na_hora_e_tira_o_destaque(aplicacao, cenario):
    base, contas, f, pagina = cenario
    painel = pagina.ficha.aba_cadastros
    conta = painel.itens[0]
    texto_da_linha = painel.tabela.cellWidget(0, 0).findChildren(type(painel.vazia))
    assert any("Não cadastrada" in t.text() for t in texto_da_linha)
    assert pagina.ficha.excluir.isVisibleTo(pagina.ficha)
    painel.caixa(conta, contas[0]).setChecked(True)
    assert marcacoes_do_item(base.conexao, conta) == {contas[0]}
    texto_da_linha = painel.tabela.cellWidget(0, 0).findChildren(type(painel.vazia))
    assert not any("Não cadastrada" in t.text() for t in texto_da_linha)
    assert not pagina.ficha.excluir.isVisibleTo(pagina.ficha)
    painel.caixa(conta, contas[0]).setChecked(False)
    assert marcacoes_do_item(base.conexao, conta) == set()


def test_marcar_todas_pede_confirmacao(aplicacao, cenario, monkeypatch):
    base, contas, f, pagina = cenario
    painel = pagina.ficha.aba_cadastros
    chave = painel.itens[1]
    perguntas = []
    monkeypatch.setattr(telas, "perguntar", lambda *args: perguntas.append(args[1]) or False)
    painel.botoes_todas[1].click()
    assert perguntas == ["Marcar todas as contas?"]
    assert marcacoes_do_item(base.conexao, chave) == set()
    monkeypatch.setattr(telas, "perguntar", lambda *args: True)
    painel.botoes_todas[1].click()
    assert marcacoes_do_item(base.conexao, chave) == set(contas)
    assert painel.caixa(chave, contas[1]).isChecked()


def test_fornecedor_inativo_nao_edita_e_guarda(aplicacao, cenario):
    base, contas, f, pagina = cenario
    painel = pagina.ficha.aba_cadastros
    painel.caixa(painel.itens[0], contas[0]).setChecked(True)
    definir_fornecedor_ativo(base.conexao, f, False)
    pagina.abrir_ficha(f)
    assert painel.situacao.isVisibleTo(painel)
    assert not painel.caixa(painel.itens[0], contas[0]).isEnabled()
    assert painel.caixa(painel.itens[0], contas[0]).isChecked()


def test_conta_da_entidade_inativa_some_da_grade(aplicacao, cenario):
    base, contas, f, pagina = cenario
    painel = pagina.ficha.aba_cadastros
    definir_ativa(base.conexao, contas[1], False)
    pagina.abrir_ficha(f)
    assert painel.tabela.columnCount() == 3
    assert "contas inativas da entidade" in painel.rodape.text()


def test_sem_contas_da_entidade_explica_o_que_fazer(aplicacao, tmp_path):
    base = BaseDeDados.criar(tmp_path / "dados.baliza", SENHA)[0]
    f = cadastrar_fornecedor(base.conexao, DadosFornecedor("pf", "529.982.247-25", "Maria"))
    pagina = PaginaFornecedores(base)
    pagina.abrir_ficha(f)
    assert "Entidade › Contas" in pagina.ficha.aba_cadastros.vazia.text()
    assert itens_do_fornecedor(base.conexao, f) == []


def test_colunas_na_mesma_ordem_da_consulta(aplicacao, cenario):
    """A ordem é a de cadastro, como na Consulta e na impressão, não a alfabética."""
    base, contas, f, pagina = cenario
    cadastrar_conta(base.conexao, DadosConta("Conta Apoio", "001", "1234-5", "11111-1"))
    pagina.abrir_ficha(f)
    painel = pagina.ficha.aba_cadastros
    cabecalho = [painel.tabela.horizontalHeaderItem(i).text() for i in range(1, 4)]
    assert cabecalho == ["Conta Movimento", "Conta Saúde", "Conta Apoio"]
