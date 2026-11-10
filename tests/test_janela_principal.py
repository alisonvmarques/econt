from econt.interface.janela_principal import JanelaPrincipal


def test_janela_abre_com_titulo_econt(aplicacao, tmp_path):
    janela = JanelaPrincipal(tmp_path / "dados.econt")
    janela.show()
    aplicacao.processEvents()

    assert janela.isVisible()
    assert janela.windowTitle() == "ECont"
    assert janela.width() >= 1024
    janela.close()
