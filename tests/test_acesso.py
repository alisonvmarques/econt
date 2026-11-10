"""Fluxos de acesso pela tela, sem janela visível (T01, T02, T04, T05)."""

from econt.dados.banco import BaseDeDados
from econt.interface.acesso import (
    TelaChaveRecuperacao,
    TelaCriarSenha,
    TelaEntrada,
    TelaNovaSenha,
)
from econt.interface.entidade import TelaDadosEntidade
from econt.interface.janela_principal import JanelaPrincipal

SENHA = "fundo2026saude"


def _criar_pela_tela(janela: JanelaPrincipal) -> str:
    tela = janela.tela_atual()
    assert isinstance(tela, TelaCriarSenha)
    tela.senha.definir(SENHA)
    tela.confirma.definir(SENHA)
    tela.criar.click()
    chave_tela = janela.tela_atual()
    assert isinstance(chave_tela, TelaChaveRecuperacao)
    return chave_tela.chave


def test_primeiro_uso_pede_senha_e_recusa_senha_fraca(aplicacao, tmp_path):
    janela = JanelaPrincipal(tmp_path / "dados.econt")
    tela = janela.tela_atual()
    assert isinstance(tela, TelaCriarSenha)
    tela.senha.definir("curta1")
    tela.confirma.definir("curta1")
    tela.criar.click()
    assert tela.senha.tem_erro()
    assert "falta pelo menos 10 caracteres" in tela.senha.linha_ajuda.text()
    assert not (tmp_path / "dados.econt").exists()


def test_confirmacao_diferente_e_recusada(aplicacao, tmp_path):
    janela = JanelaPrincipal(tmp_path / "dados.econt")
    tela = janela.tela_atual()
    tela.senha.definir(SENHA)
    tela.confirma.definir(SENHA + "x")
    tela.criar.click()
    assert tela.confirma.tem_erro()
    assert isinstance(janela.tela_atual(), TelaCriarSenha)


def test_senha_nunca_fica_em_texto_puro(aplicacao, tmp_path):
    caminho = tmp_path / "dados.econt"
    janela = JanelaPrincipal(caminho)
    _criar_pela_tela(janela)
    assert SENHA.encode() not in caminho.read_bytes()
    janela.close()


def test_chave_so_segue_depois_de_confirmar_que_guardou(aplicacao, tmp_path):
    janela = JanelaPrincipal(tmp_path / "dados.econt")
    _criar_pela_tela(janela)
    tela = janela.tela_atual()
    assert not tela.botao_continuar.isEnabled()
    tela.guardei.setChecked(True)
    assert tela.botao_continuar.isEnabled()
    tela.botao_continuar.click()
    assert isinstance(janela.tela_atual(), TelaDadosEntidade)
    janela.close()


def test_chave_salva_em_pdf(aplicacao, tmp_path):
    janela = JanelaPrincipal(tmp_path / "dados.econt")
    _criar_pela_tela(janela)
    pdf = tmp_path / "chave.pdf"
    janela.tela_atual().gravar_pdf(str(pdf))
    assert pdf.read_bytes().startswith(b"%PDF")
    janela.close()


def test_entrada_com_senha_certa_e_errada(aplicacao, tmp_path):
    caminho = tmp_path / "dados.econt"
    BaseDeDados.criar(caminho, SENHA)[0].fechar()
    janela = JanelaPrincipal(caminho)
    tela = janela.tela_atual()
    assert isinstance(tela, TelaEntrada)

    tela.senha.definir("senha-errada-1")
    tela.entrar.click()
    assert tela.erro.isVisibleTo(tela) and "Senha incorreta" in tela.erro.text()
    assert janela.base is None

    tela.senha.definir(SENHA)
    tela.entrar.click()
    assert janela.base is not None
    janela.close()


def test_esqueci_a_senha_com_chave_certa_e_errada(aplicacao, tmp_path):
    caminho = tmp_path / "dados.econt"
    base, chave = BaseDeDados.criar(caminho, SENHA)
    base.conexao.execute("INSERT INTO banco VALUES ('999', NULL, 'Banco Fictício', 'manual')")
    base.fechar()
    janela = JanelaPrincipal(caminho)
    janela.tela_atual().link_esqueci.click()
    tela = janela.tela_atual()
    assert isinstance(tela, TelaNovaSenha)

    tela.chave.definir("AAAA-BBBB-CCCC-DDDD-EEEE-FFFF")
    tela.senha.definir("nova2026senha")
    tela.confirma.definir("nova2026senha")
    tela.criar.click()
    assert tela.chave.tem_erro()
    assert isinstance(janela.tela_atual(), TelaNovaSenha)

    tela.chave.definir(chave.lower())
    tela.criar.click()
    janela.close()

    aberta = BaseDeDados.abrir(caminho, senha="nova2026senha")
    assert aberta.conexao.execute("SELECT nome FROM banco WHERE codigo='999'").fetchone()


def test_chave_nao_confirmada_e_trocada_e_mostrada_de_novo(aplicacao, tmp_path):
    """Fechou o sistema na tela da chave sem confirmar: na próxima entrada, uma chave nova."""
    caminho = tmp_path / "dados.econt"
    janela = JanelaPrincipal(caminho)
    chave_perdida = _criar_pela_tela(janela)
    janela.close()

    janela = JanelaPrincipal(caminho)
    entrada = janela.tela_atual()
    entrada.senha.definir(SENHA)
    entrada.entrar.click()
    tela = janela.tela_atual()
    assert isinstance(tela, TelaChaveRecuperacao)
    assert tela.chave != chave_perdida
    tela.guardei.setChecked(True)
    tela.botao_continuar.click()
    assert isinstance(janela.tela_atual(), TelaDadosEntidade)
    janela.close()

    BaseDeDados.abrir(caminho, chave=tela.chave)  # a nova chave abre os dados
    janela = JanelaPrincipal(caminho)
    entrada = janela.tela_atual()
    entrada.senha.definir(SENHA)
    entrada.entrar.click()
    assert isinstance(janela.tela_atual(), TelaDadosEntidade)  # não pede a chave de novo
    janela.close()
