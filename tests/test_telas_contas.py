from datetime import datetime, timedelta

import pytest

from econt.dados.banco import BaseDeDados
from econt.dados.contas import DadosConta, cadastrar_conta, listar_contas, obter_conta
from econt.dados.entidade import Entidade, salvar_entidade
from econt.dados.lista_bancos import cadastrar_banco_manual
from econt.interface import contas as telas_contas
from econt.interface.area_principal import AreaPrincipal
from econt.interface.contas import PaginaContas

SENHA = "fundo2026saude"
AGORA = datetime(2026, 11, 8, 10, 15)


@pytest.fixture
def base(tmp_path):
    base = BaseDeDados.criar(tmp_path / "dados.econt", SENHA)[0]
    salvar_entidade(base.conexao, Entidade("Fundo de Saúde Exemplo", "11.222.333/0001-81"))
    return base


def _pagina(base, agora=AGORA):
    relogio = {"agora": agora}
    pagina = PaginaContas(base, lambda: relogio["agora"])
    return pagina, relogio


def _dialogo_preenchido(pagina, monkeypatch, descricao, banco, agencia, conta):
    """Abre o formulário de nova conta, preenche e confirma, sem janela modal."""
    original = pagina.criar_dialogo

    def criar(conta_atual):
        dialogo = original(conta_atual)
        dialogo.descricao.definir(descricao)
        dialogo.banco.definir(banco)
        dialogo.agencia.definir(agencia)
        dialogo.numero.definir(conta)
        dialogo.exec = lambda: (dialogo.confirmar.click(), dialogo.result())[1]
        return dialogo

    monkeypatch.setattr(pagina, "criar_dialogo", criar)


def test_area_entidade_tem_dados_e_contas(aplicacao, base):
    area = AreaPrincipal(base)
    area.navegacao.botoes["entidade"].click()
    pagina = area.paginas.currentWidget()
    assert [pagina.abas.tabText(i) for i in range(pagina.abas.count())] == ["Dados", "Contas"]
    assert isinstance(pagina.contas, PaginaContas)


def test_nova_conta_pelo_formulario(aplicacao, base, monkeypatch):
    pagina, _ = _pagina(base)
    assert pagina.lista.vazia.isVisibleTo(pagina.lista)
    _dialogo_preenchido(pagina, monkeypatch, "Conta Movimento", "001", "1234-5", "55555-0")
    pagina.lista.nova.click()
    assert pagina.currentWidget() is pagina.detalhe
    assert pagina.detalhe.titulo.text() == "Conta Movimento · 001 · Ag. 1234-5 · C/C 55555-0"
    assert pagina.detalhe.tabela.item(0, 1).text() == "R$ 10.000,00"
    assert pagina.detalhe.tabela.item(1, 1).text() == "R$ 10.000,00"
    pagina.detalhe.voltar.click()
    tabela = pagina.lista.tabela
    assert tabela.rowCount() == 1
    assert tabela.item(0, 1).text() == "001 · Ag. 1234-5 · C/C 55555-0"


def test_formulario_mostra_o_erro_no_campo(aplicacao, base):
    pagina, _ = _pagina(base)
    dialogo = pagina.criar_dialogo(None)
    dialogo.descricao.definir("Conta Movimento")
    dialogo.banco.definir("001")
    dialogo.agencia.definir("1234")
    dialogo.numero.definir("555550")
    dialogo.confirmar.click()
    assert dialogo.numero.tem_erro()
    assert "dígito" in dialogo.numero.linha_ajuda.text()
    assert not dialogo.agencia.tem_erro()
    assert listar_contas(base.conexao) == []


def test_editar_conta_pelo_formulario(aplicacao, base):
    conta_id = cadastrar_conta(base.conexao, DadosConta("Conta A", "001", "1", "1-1"))
    pagina, _ = _pagina(base)
    pagina.abrir_conta(conta_id)
    dialogo = pagina.criar_dialogo(pagina._conta())
    assert dialogo.banco.valor() == "001"
    dialogo.descricao.definir("Conta Pix")
    dialogo.confirmar.click()
    assert obter_conta(base.conexao, conta_id).descricao == "Conta Pix"


def test_pedido_fica_em_liberacao_e_depois_passa_a_valer(aplicacao, base):
    conta_id = cadastrar_conta(base.conexao, DadosConta("Conta Pix", "001", "1234-5", "66666-2"))
    pagina, relogio = _pagina(base)
    pagina.abrir_conta(conta_id)
    detalhe = pagina.detalhe
    detalhe.tipo.definir("pix")
    detalhe.valor.definir("30000")
    detalhe.pedido_em.definir(datetime(2026, 11, 7, 14, 30))
    detalhe.registrar.click()
    assert "passa a R$ 30.000,00 em 08/11/2026 às 14:30" in detalhe.retorno.text()
    assert detalhe.tabela.item(0, 1).text() == "R$ 10.000,00"
    assert detalhe.tabela.item(0, 2).text() == "R$ 30.000,00"
    assert detalhe.tabela.item(1, 2).text() == "—"
    assert detalhe.avisos.count() == 1
    assert "em liberação" in detalhe.avisos.itemAt(0).widget().text()

    relogio["agora"] = AGORA + timedelta(hours=5)
    pagina.atualizar()
    assert detalhe.tabela.item(0, 1).text() == "R$ 30.000,00"
    assert detalhe.tabela.item(0, 2).text() == "—"
    assert detalhe.avisos.count() == 0


def test_pedido_com_erro_mostra_no_campo(aplicacao, base):
    conta_id = cadastrar_conta(base.conexao, DadosConta("Conta Pix", "001", "1234-5", "66666-2"))
    pagina, _ = _pagina(base)
    pagina.abrir_conta(conta_id)
    detalhe = pagina.detalhe
    detalhe.valor.definir("abc")
    detalhe.registrar.click()
    assert detalhe.valor.tem_erro()
    detalhe.valor.definir("25.000,00")
    detalhe.pedido_em.definir(AGORA + timedelta(days=1))
    detalhe.registrar.click()
    assert detalhe.pedido_em.tem_erro()
    assert obter_conta(base.conexao, conta_id).pix.em_liberacao is None


def test_inativar_pede_confirmacao(aplicacao, base, monkeypatch):
    conta_id = cadastrar_conta(base.conexao, DadosConta("Conta Pix", "001", "1234-5", "66666-2"))
    pagina, _ = _pagina(base)
    pagina.abrir_conta(conta_id)
    respostas = []
    monkeypatch.setattr(telas_contas, "perguntar", lambda *args: respostas.append(args[1]) or False)
    pagina.detalhe.ativar.click()
    assert respostas == ["Inativar conta"]
    assert obter_conta(base.conexao, conta_id).ativa
    monkeypatch.setattr(telas_contas, "perguntar", lambda *args: True)
    pagina.detalhe.ativar.click()
    assert not obter_conta(base.conexao, conta_id).ativa
    assert pagina.detalhe.ativar.text() == "Reativar conta"
    assert not pagina.detalhe.formulario.isEnabled()
    pagina.detalhe.ativar.click()
    assert obter_conta(base.conexao, conta_id).ativa


def test_banco_manual_aparece_na_escolha_das_contas(aplicacao, base):
    cadastrar_banco_manual(base.conexao, "999", "Banco Fictício Cooperativo")
    pagina, _ = _pagina(base)
    dialogo = pagina.criar_dialogo(None)
    dialogo.banco.definir("999")
    assert dialogo.banco.valor() == "999"
    assert "999 · Banco Fictício Cooperativo" in [
        dialogo.banco.caixa.itemText(i) for i in range(dialogo.banco.caixa.count())
    ]
