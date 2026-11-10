import sqlite3

from econt.dados.banco import MIGRACOES
from econt.dados.lista_bancos import bancos_oficiais, carregar_bancos_oficiais


def _base_vazia():
    conexao = sqlite3.connect(":memory:")
    conexao.executescript(MIGRACOES[0])
    return conexao


def test_bancos_conhecidos_estao_na_lista():
    bancos = {b.codigo: b for b in bancos_oficiais()}
    assert bancos["001"].nome == "Banco do Brasil S.A."
    assert bancos["104"].nome == "CAIXA ECONOMICA FEDERAL"
    assert bancos["237"].nome == "Banco Bradesco S.A."
    assert bancos["341"].ispb == "60701190"


def test_codigos_tem_tres_digitos_e_nao_se_repetem():
    codigos = [b.codigo for b in bancos_oficiais()]
    assert all(len(c) == 3 and c.isdigit() for c in codigos)
    assert len(codigos) == len(set(codigos)) > 400


def test_carga_preserva_bancos_manuais():
    conexao = _base_vazia()
    conexao.execute("INSERT INTO banco VALUES ('001', NULL, 'Nome Manual', 'manual')")
    carregar_bancos_oficiais(conexao)
    linha = conexao.execute("SELECT nome, origem FROM banco WHERE codigo='001'").fetchone()
    assert linha == ("Nome Manual", "manual")
    assert conexao.execute("SELECT count(*) FROM banco").fetchone()[0] > 400
