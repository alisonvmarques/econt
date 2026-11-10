import os

from econt.app import icone_do_econt, verificar


def test_verificar_abre_tudo_sem_tocar_nos_dados(aplicacao, tmp_path, monkeypatch):
    monkeypatch.setenv("ECONT_ARQUIVO", str(tmp_path / "dados-de-verdade.econt"))
    relatorio = tmp_path / "relatorio.txt"
    assert verificar(str(relatorio)) == 0
    texto = relatorio.read_text(encoding="utf-8")
    assert "resultado: ok" in texto
    assert "criptografia: ok" in texto
    assert "janela: TelaCriarSenha" in texto
    assert not (tmp_path / "dados-de-verdade.econt").exists()
    assert os.environ["ECONT_ARQUIVO"] == str(tmp_path / "dados-de-verdade.econt")


def test_icone_do_econt(aplicacao):
    assert not icone_do_econt().isNull()


def test_erro_inesperado_em_portugues():
    import errno

    from econt.app import MENSAGEM_DE_ERRO, mensagem_de_erro_inesperado

    assert "espaço no disco" in mensagem_de_erro_inesperado(OSError(errno.ENOSPC, "No space"))
    assert "permissão" in mensagem_de_erro_inesperado(PermissionError(13, "denied"))
    assert mensagem_de_erro_inesperado(RuntimeError("x")) == MENSAGEM_DE_ERRO
    assert "continuam no arquivo" in MENSAGEM_DE_ERRO


def test_barra_de_tarefas_acha_o_icone_pelo_atalho(aplicacao):
    """Linux: o nome do atalho (Wayland) e a classe da janela (X11) batem com o .desktop."""
    from pathlib import Path

    from econt.app import criar_aplicacao

    app = criar_aplicacao()
    atalho = Path(__file__).parent.parent / "empacotamento" / "linux" / "econt.desktop"
    assert app.desktopFileName() == atalho.stem
    assert f"StartupWMClass={app.applicationName()}" in atalho.read_text(encoding="utf-8")
