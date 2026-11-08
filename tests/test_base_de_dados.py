import sqlite3

import pytest

from baliza.dados.banco import MIGRACOES, BaseDeDados, versao_atual
from baliza.dados.cofre import SenhaIncorreta

SENHA = "senha-de-teste-123"


def test_cria_e_reabre_com_senha_e_com_chave(tmp_path):
    caminho = tmp_path / "dados.baliza"
    base, chave = BaseDeDados.criar(caminho, SENHA)
    base.conexao.execute("INSERT INTO banco VALUES ('999', NULL, 'Banco Fictício', 'manual')")
    base.fechar()

    for aberta in (
        BaseDeDados.abrir(caminho, senha=SENHA),
        BaseDeDados.abrir(caminho, chave=chave),
    ):
        nome = aberta.conexao.execute("SELECT nome FROM banco WHERE codigo='999'").fetchone()[0]
        assert nome == "Banco Fictício"
        assert aberta.versao() == versao_atual()


def test_nada_e_gravado_em_texto_puro(tmp_path):
    caminho = tmp_path / "dados.baliza"
    base, _ = BaseDeDados.criar(caminho, SENHA)
    base.conexao.execute("INSERT INTO banco VALUES ('998', NULL, 'Fornecedor Secreto', 'manual')")
    base.fechar()
    conteudo = caminho.read_bytes()
    assert b"Fornecedor Secreto" not in conteudo
    assert b"SQLite format" not in conteudo


def test_senha_errada(tmp_path):
    caminho = tmp_path / "dados.baliza"
    BaseDeDados.criar(caminho, SENHA)[0].fechar()
    with pytest.raises(SenhaIncorreta):
        BaseDeDados.abrir(caminho, senha="errada")


def test_migracao_de_uma_versao_antiga(tmp_path, monkeypatch):
    """Uma versão futura acrescenta uma migração; os dados antigos continuam lá."""
    caminho = tmp_path / "dados.baliza"
    base, _ = BaseDeDados.criar(caminho, SENHA)
    base.fechar()

    nova = "CREATE TABLE exemplo_futuro (id INTEGER PRIMARY KEY, nome TEXT NOT NULL);"
    monkeypatch.setattr("baliza.dados.banco.MIGRACOES", [*MIGRACOES, nova])
    aberta = BaseDeDados.abrir(caminho, senha=SENHA)
    assert aberta.versao() == len(MIGRACOES) + 1
    aberta.conexao.execute("INSERT INTO exemplo_futuro (nome) VALUES ('Teste')")
    assert aberta.conexao.execute("SELECT count(*) FROM banco").fetchone()[0] > 400


def test_dados_de_versao_mais_nova_nao_abrem(tmp_path):
    caminho = tmp_path / "dados.baliza"
    base, _ = BaseDeDados.criar(caminho, SENHA)
    base.conexao.execute("PRAGMA user_version = 99")
    base.fechar()
    with pytest.raises(RuntimeError, match="versão mais nova"):
        BaseDeDados.abrir(caminho, senha=SENHA)


def test_sqlite_tem_serialize():
    assert hasattr(sqlite3.Connection, "serialize")
