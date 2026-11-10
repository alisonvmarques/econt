import sqlite3

import pytest

from econt.dados.banco import BaseDeDados
from econt.dados.lista_bancos import (
    BancoInvalido,
    cadastrar_banco_manual,
    listar_bancos,
    obter_banco,
)
from econt.interface.bancos import PaginaBancos
from econt.interface.configuracoes import PaginaConfiguracoes

SENHA = "fundo2026saude"


@pytest.fixture
def base(tmp_path):
    return BaseDeDados.criar(tmp_path / "dados.econt", SENHA)[0]


def test_banco_manual_entra_na_lista(base):
    banco = cadastrar_banco_manual(base.conexao, "999", "Banco Fictício Cooperativo")
    assert banco.origem == "manual"
    assert banco.rotulo == "999 · Banco Fictício Cooperativo"
    assert banco in listar_bancos(base.conexao)
    assert listar_bancos(base.conexao, "fictício") == [banco]


def test_banco_manual_nao_repete_codigo(base):
    with pytest.raises(BancoInvalido, match="001 já é do Banco do Brasil"):
        cadastrar_banco_manual(base.conexao, "1", "Outro Banco")
    cadastrar_banco_manual(base.conexao, "998", "Banco Exemplo")
    with pytest.raises(BancoInvalido, match="998 já é do Banco Exemplo"):
        cadastrar_banco_manual(base.conexao, "998", "Banco Repetido")
    with pytest.raises(BancoInvalido, match="até 3 números"):
        cadastrar_banco_manual(base.conexao, "12A", "Banco")
    with pytest.raises(BancoInvalido, match="nome"):
        cadastrar_banco_manual(base.conexao, "997", "  ")
    with pytest.raises(sqlite3.IntegrityError):
        base.conexao.execute("INSERT INTO banco VALUES ('998', NULL, 'X', 'manual')")


def test_lista_oficial_nao_sobrescreve_banco_manual(base):
    from econt.dados.lista_bancos import carregar_bancos_oficiais

    cadastrar_banco_manual(base.conexao, "999", "Banco Fictício Cooperativo")
    carregar_bancos_oficiais(base.conexao)
    assert obter_banco(base.conexao, "999").nome == "Banco Fictício Cooperativo"


def test_configuracoes_tem_a_aba_bancos(aplicacao, base):
    pagina = PaginaConfiguracoes(base)
    assert [pagina.abas.tabText(i) for i in range(3)] == ["Impressão", "Backup", "Bancos"]


def test_banco_manual_pela_tela(aplicacao, base, monkeypatch):
    bancos = PaginaBancos(base)
    original = bancos.criar_dialogo

    def criar():
        dialogo = original()
        dialogo.codigo.definir("999")
        dialogo.nome.definir("Banco Fictício Cooperativo")
        dialogo.exec = lambda: (dialogo.confirmar.click(), dialogo.result())[1]
        return dialogo

    monkeypatch.setattr(bancos, "criar_dialogo", criar)
    bancos.cadastrar.click()
    assert obter_banco(base.conexao, "999").origem == "manual"
    assert bancos.tabela.rowCount() == 1
    assert bancos.tabela.item(0, 1).text() == "Banco Fictício Cooperativo"


def test_banco_com_codigo_repetido_mostra_o_erro(aplicacao, base):
    bancos = PaginaBancos(base)
    dialogo = bancos.criar_dialogo()
    dialogo.codigo.definir("001")
    dialogo.nome.definir("Outro")
    dialogo.confirmar.click()
    assert dialogo.codigo.tem_erro()
    assert "Banco do Brasil" in dialogo.codigo.linha_ajuda.text()


def test_busca_de_bancos(aplicacao, base):
    bancos = PaginaBancos(base)
    total = bancos.tabela.rowCount()
    assert total > 400
    bancos.busca.setText("caixa econ")
    assert bancos.tabela.rowCount() == 1
    assert bancos.tabela.item(0, 0).text() == "104"
