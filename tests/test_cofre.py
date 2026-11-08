import pytest

from baliza.dados.cofre import (
    ArquivoInvalido,
    ChaveIncorreta,
    Cofre,
    SenhaIncorreta,
    gerar_chave_recuperacao,
)

SENHA = "senha-de-teste-123"


def test_texto_gravado_nao_aparece_no_arquivo(tmp_path):
    caminho = tmp_path / "dados.baliza"
    Cofre.criar(caminho, SENHA, b"Distribuidora Exemplo de Materiais Ltda")
    assert b"Distribuidora Exemplo" not in caminho.read_bytes()


def test_abre_com_a_senha_e_com_a_chave(tmp_path):
    caminho = tmp_path / "dados.baliza"
    _, chave = Cofre.criar(caminho, SENHA, b"conteudo")
    assert Cofre.abrir_com_senha(caminho, SENHA).ler() == b"conteudo"
    assert Cofre.abrir_com_chave(caminho, chave).ler() == b"conteudo"
    assert Cofre.abrir_com_chave(caminho, chave.lower().replace("-", " ")).ler() == b"conteudo"


def test_senha_errada_falha_com_mensagem_em_portugues(tmp_path):
    caminho = tmp_path / "dados.baliza"
    Cofre.criar(caminho, SENHA)
    with pytest.raises(SenhaIncorreta, match="Senha incorreta"):
        Cofre.abrir_com_senha(caminho, "outra-senha")


def test_chave_errada_falha(tmp_path):
    caminho = tmp_path / "dados.baliza"
    Cofre.criar(caminho, SENHA)
    with pytest.raises(ChaveIncorreta):
        Cofre.abrir_com_chave(caminho, gerar_chave_recuperacao())


def test_trocar_senha_mantem_os_dados_e_a_chave(tmp_path):
    caminho = tmp_path / "dados.baliza"
    cofre, chave = Cofre.criar(caminho, SENHA, b"conteudo")
    cofre.trocar_senha("nova-senha-456")
    with pytest.raises(SenhaIncorreta):
        Cofre.abrir_com_senha(caminho, SENHA)
    assert Cofre.abrir_com_senha(caminho, "nova-senha-456").ler() == b"conteudo"
    assert Cofre.abrir_com_chave(caminho, chave).ler() == b"conteudo"


def test_nova_chave_invalida_a_anterior(tmp_path):
    caminho = tmp_path / "dados.baliza"
    cofre, antiga = Cofre.criar(caminho, SENHA)
    nova = cofre.gerar_nova_chave()
    with pytest.raises(ChaveIncorreta):
        Cofre.abrir_com_chave(caminho, antiga)
    Cofre.abrir_com_chave(caminho, nova)


def test_arquivo_que_nao_e_do_baliza(tmp_path):
    caminho = tmp_path / "qualquer.baliza"
    caminho.write_bytes(b"isto nao e um arquivo do baliza")
    with pytest.raises(ArquivoInvalido):
        Cofre.abrir_com_senha(caminho, SENHA)


def test_formato_da_chave_de_recuperacao():
    chave = gerar_chave_recuperacao()
    blocos = chave.split("-")
    assert len(blocos) == 6 and all(len(b) == 4 for b in blocos)
    assert not set(chave) & set("IO01")
