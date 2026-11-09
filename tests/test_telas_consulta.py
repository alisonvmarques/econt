import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest

from baliza.dados.banco import BaseDeDados
from baliza.dados.contas import DadosConta, cadastrar_conta
from baliza.dados.entidade import Entidade, salvar_entidade
from baliza.dados.fornecedores import (
    DadosContaFornecedor,
    DadosFornecedor,
    cadastrar_fornecedor,
    definir_fornecedor_ativo,
    salvar_chave_pix,
    salvar_conta_fornecedor,
)
from baliza.dados.marcacoes import itens_do_fornecedor, marcar_todas
from baliza.interface import consulta as telas
from baliza.interface import fornecedores as telas_fornecedores
from baliza.interface.area_principal import AreaPrincipal
from baliza.interface.configuracoes import PaginaConfiguracoes
from baliza.interface.consulta import PaginaConsulta, formato_escolhido

SENHA = "fundo2026saude"


@pytest.fixture
def cenario(tmp_path):
    base = BaseDeDados.criar(tmp_path / "dados.baliza", SENHA)[0]
    c = base.conexao
    salvar_entidade(c, Entidade("Fundo de Saúde Exemplo", "11.222.333/0001-81"))
    cadastrar_conta(c, DadosConta("Conta Movimento", "001", "1234-5", "55555-0"))
    cadastrar_conta(c, DadosConta("Conta Saúde", "104", "0456", "77777-1"))
    a = cadastrar_fornecedor(
        c, DadosFornecedor("pj", "11.222.333/0001-81", "Distribuidora Exemplo de Materiais Ltda")
    )
    salvar_conta_fornecedor(c, a, DadosContaFornecedor("001", "1234-5", "98765-4"))
    salvar_chave_pix(c, a, "email", "financeiro@exemplo.com.br")
    marcar_todas(c, itens_do_fornecedor(c, a)[0])
    b = cadastrar_fornecedor(
        c, DadosFornecedor("pj", "12.ABC.345/01DE-35", "Distribuidora Modelo Hospitalar Ltda")
    )
    salvar_conta_fornecedor(c, b, DadosContaFornecedor("237", "0101", "22222-3"))
    marcar_todas(c, itens_do_fornecedor(c, b)[0])
    return base, a, b


@pytest.fixture
def impressoes(monkeypatch):
    abertas = []

    def abrir(pai, impressao):
        abertas.append(impressao)
        return True

    monkeypatch.setattr(telas, "abrir_janela_impressao", abrir)
    return abertas


def test_area_consulta(aplicacao, cenario):
    area = AreaPrincipal(cenario[0])
    area.navegacao.botoes["consulta"].click()
    assert isinstance(area.paginas.currentWidget(), PaginaConsulta)


def test_busca_lista_e_destaca(aplicacao, cenario):
    base, a, b = cenario
    pagina = PaginaConsulta(base)
    pagina.busca.setText("DISTRI")
    assert pagina.quantos.text() == "2 fornecedores encontrados"
    assert pagina.lista.count() == 2
    linha = pagina.lista.itemWidget(pagina.lista.item(0))
    assert "<b" in linha.findChildren(type(pagina.quantos))[0].text()
    pagina.busca.setText("hospitalar")
    assert pagina.lista.count() == 1
    pagina.busca.setText("nada parecido")
    assert "Nenhum fornecedor ativo" in pagina.quantos.text()


def test_inativo_nao_aparece(aplicacao, cenario):
    base, a, b = cenario
    definir_fornecedor_ativo(base.conexao, b, False)
    pagina = PaginaConsulta(base)
    pagina.busca.setText("distri")
    assert pagina.lista.count() == 1


def test_enter_abre_o_resultado_com_o_aviso(aplicacao, cenario):
    base, a, b = cenario
    pagina = PaginaConsulta(base)
    pagina.busca.setText("materiais")
    QTest.keyClick(pagina.busca, Qt.Key.Key_Return)
    resultado = pagina.resultado
    assert pagina.areas.currentWidget() is resultado
    assert resultado.nome.text() == "Distribuidora Exemplo de Materiais Ltda"
    cabecalho = [
        resultado.tabela.horizontalHeaderItem(i).text()
        for i in range(resultado.tabela.columnCount())
    ]
    assert cabecalho == ["Conta ou chave", "Dados", "Conta Movimento", "Conta Saúde"]
    assert resultado.tabela.rowCount() == 2
    assert resultado.alerta.isVisibleTo(resultado)
    assert "financeiro@exemplo.com.br não está cadastrada" in resultado.alerta.text()
    assert resultado.conferido.text().startswith("Conferido em ")
    resultado.voltar.click()
    assert pagina.areas.currentWidget() is pagina.lista_area


def test_meia_folha_imprime_um_por_vez(aplicacao, cenario, impressoes):
    base, a, b = cenario
    base.definir_configuracao("formato_impressao", "meia_folha")
    pagina = PaginaConsulta(base)
    pagina.abrir(a)
    pagina.resultado.imprimir.click()
    assert len(impressoes) == 1 and len(impressoes[0].blocos) == 1


def test_folha_completa_guarda_e_junta_com_o_proximo(aplicacao, cenario, impressoes, monkeypatch):
    base, a, b = cenario
    pagina = PaginaConsulta(base)
    monkeypatch.setattr(telas, "escolher", lambda *args: 1)
    pagina.abrir(a)
    pagina.resultado.imprimir.click()
    assert impressoes == []
    assert pagina.na_fila.fornecedor.id == a
    pagina.abrir(b)
    assert pagina.resultado.fila.isVisibleTo(pagina.resultado)
    pagina.resultado.imprimir.click()
    assert len(impressoes) == 1
    blocos = impressoes[0].blocos
    assert "Materiais" in blocos[0] and "Hospitalar" in blocos[1]
    assert pagina.na_fila is None


def test_folha_completa_pode_sair_sozinha(aplicacao, cenario, impressoes, monkeypatch):
    base, a, _ = cenario
    pagina = PaginaConsulta(base)
    monkeypatch.setattr(telas, "escolher", lambda *args: 0)
    pagina.abrir(a)
    pagina.resultado.imprimir.click()
    assert len(impressoes) == 1 and len(impressoes[0].blocos) == 1


def test_formato_escolhido_nas_configuracoes(aplicacao, cenario):
    base = cenario[0]
    assert formato_escolhido(base) == "folha_completa"
    pagina = PaginaConfiguracoes(base)
    assert pagina.impressao.opcoes["folha_completa"].isChecked()
    pagina.impressao.opcoes["meia_folha"].setChecked(True)
    assert formato_escolhido(base) == "meia_folha"
    assert "Meia folha" in pagina.impressao.retorno.text()
    reaberta = PaginaConfiguracoes(base)
    assert reaberta.impressao.opcoes["meia_folha"].isChecked()


def test_ficha_imprime_a_ficha_completa(aplicacao, cenario, monkeypatch):
    base, a, _ = cenario
    abertas = []
    monkeypatch.setattr(
        telas_fornecedores, "abrir_janela_impressao", lambda pai, imp: abertas.append(imp)
    )
    pagina = telas_fornecedores.PaginaFornecedores(base)
    pagina.abrir_ficha(a)
    pagina.ficha.imprimir.click()
    assert abertas[0].titulo == "Ficha do fornecedor"
    assert "Distribuidora Exemplo de Materiais Ltda" in abertas[0].html
