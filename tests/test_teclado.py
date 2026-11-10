"""RNF05: os fluxos principais funcionam só pelo teclado."""

import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from econt.dados.banco import BaseDeDados
from econt.dados.contas import DadosConta, cadastrar_conta, listar_contas, obter_conta
from econt.dados.entidade import Entidade, salvar_entidade
from econt.dados.fornecedores import (
    DadosContaFornecedor,
    DadosFornecedor,
    cadastrar_fornecedor,
    listar_chaves,
    listar_fornecedores,
    salvar_conta_fornecedor,
)
from econt.dados.marcacoes import itens_do_fornecedor, marcacoes_do_item
from econt.interface.area_principal import AreaPrincipal
from econt.interface.contas import PaginaContas
from econt.interface.fornecedores import PaginaFornecedores

SENHA = "fundo2026saude"


@pytest.fixture
def base(tmp_path):
    base = BaseDeDados.criar(tmp_path / "dados.econt", SENHA)[0]
    salvar_entidade(base.conexao, Entidade("Fundo de Saúde Exemplo", "11.222.333/0001-81"))
    return base


def _mostrar(janela):
    """Mostra e ativa a janela, como quando a pessoa clica nela."""
    janela.show()
    janela.activateWindow()
    QTest.qWaitForWindowActive(janela)
    return janela


def _digitar(widget, texto):
    widget.setFocus()
    QTest.keyClicks(widget, texto)


def test_consulta_pelo_teclado(aplicacao, base):
    f = cadastrar_fornecedor(
        base.conexao, DadosFornecedor("pj", "11.222.333/0001-81", "Distribuidora Exemplo")
    )
    salvar_conta_fornecedor(base.conexao, f, DadosContaFornecedor("001", "1234-5", "98765-4"))
    area = _mostrar(AreaPrincipal(base))
    QTest.keyClick(area, Qt.Key.Key_2, Qt.KeyboardModifier.ControlModifier)
    consulta = area.indice["consulta"]
    assert area.area_atual() == "consulta"
    _digitar(consulta.busca, "distri")
    QTest.keyClick(consulta.busca, Qt.Key.Key_Return)
    assert consulta.areas.currentWidget() is consulta.resultado
    assert QApplication.focusWidget() is consulta.resultado.imprimir
    consulta.voltar_para_busca()
    QTest.keyClick(consulta.busca, Qt.Key.Key_Escape)
    assert consulta.busca.text() == ""


def test_novo_fornecedor_pelo_teclado(aplicacao, base):
    pagina = _mostrar(PaginaFornecedores(base))
    pagina.lista.novo.setFocus()
    QTest.keyClick(pagina.lista.novo, Qt.Key.Key_Space)
    form = pagina.formulario
    assert QApplication.focusWidget() is form.documento.caixa
    QTest.keyClicks(form.documento.caixa, "11222333000181")
    QTest.keyClick(form.documento.caixa, Qt.Key.Key_Tab)
    _digitar(form.razao_social.caixa, "Distribuidora Exemplo")
    QTest.keyClick(form.razao_social.caixa, Qt.Key.Key_Return)
    assert [f.razao_social for f in listar_fornecedores(base.conexao)] == ["Distribuidora Exemplo"]
    assert pagina.currentWidget() is pagina.ficha


def test_lista_de_fornecedores_abre_com_enter(aplicacao, base):
    cadastrar_fornecedor(base.conexao, DadosFornecedor("pf", "529.982.247-25", "Maria"))
    pagina = _mostrar(PaginaFornecedores(base))
    pagina.lista.tabela.setFocus()
    pagina.lista.tabela.setCurrentCell(0, 0)
    QTest.keyClick(pagina.lista.tabela, Qt.Key.Key_Return)
    assert pagina.currentWidget() is pagina.ficha


def test_dialogo_confirma_com_enter(aplicacao, base):
    f = cadastrar_fornecedor(base.conexao, DadosFornecedor("pf", "529.982.247-25", "Maria"))
    pagina = PaginaFornecedores(base)
    pagina.abrir_ficha(f)
    dialogo = pagina.ficha.criar_dialogo_chave(None)
    dialogo.show()
    dialogo.tipo.definir("email")
    _digitar(dialogo.chave.caixa, "financeiro@exemplo.com.br")
    QTest.keyClick(dialogo.chave.caixa, Qt.Key.Key_Return)
    assert [c.chave for c in listar_chaves(base.conexao, f)] == ["financeiro@exemplo.com.br"]


def test_nova_conta_da_entidade_com_enter(aplicacao, base):
    pagina = PaginaContas(base)
    dialogo = pagina.criar_dialogo(None)
    dialogo.show()
    _digitar(dialogo.descricao.caixa, "Conta Movimento")
    dialogo.banco.definir("001")
    _digitar(dialogo.agencia.caixa, "1234-5")
    _digitar(dialogo.numero.caixa, "55555-0")
    QTest.keyClick(dialogo.numero.caixa, Qt.Key.Key_Return)
    assert [c.descricao for c in listar_contas(base.conexao)] == ["Conta Movimento"]


def test_pedido_de_limite_com_enter(aplicacao, base):
    conta = cadastrar_conta(base.conexao, DadosConta("Conta Pix", "001", "1", "1-1"))
    pagina = _mostrar(PaginaContas(base))
    pagina.abrir_conta(conta)
    assert QApplication.focusWidget() is pagina.detalhe.valor.caixa
    QTest.keyClicks(pagina.detalhe.valor.caixa, "30000")
    QTest.keyClick(pagina.detalhe.valor.caixa, Qt.Key.Key_Return)
    assert obter_conta(base.conexao, conta).pix.em_liberacao.valor == 3_000_000


def test_marcacoes_com_tab_e_espaco(aplicacao, base):
    cadastrar_conta(base.conexao, DadosConta("Conta Movimento", "001", "1", "1-1"))
    f = cadastrar_fornecedor(base.conexao, DadosFornecedor("pf", "529.982.247-25", "Maria"))
    salvar_conta_fornecedor(base.conexao, f, DadosContaFornecedor("001", "1234-5", "98765-4"))
    pagina = _mostrar(PaginaFornecedores(base))
    pagina.abrir_ficha(f)
    pagina.ficha.abas.setCurrentIndex(2)
    painel = pagina.ficha.aba_cadastros
    item = itens_do_fornecedor(base.conexao, f)[0]
    caixa = painel.caixa(item, listar_contas(base.conexao)[0].id)
    assert caixa.focusPolicy() & Qt.FocusPolicy.TabFocus
    caixa.setFocus()
    QTest.keyClick(caixa, Qt.Key.Key_Space)
    assert marcacoes_do_item(base.conexao, item)
