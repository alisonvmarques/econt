from baliza.interface.janela_principal import JanelaPrincipal


def test_janela_abre_com_titulo_baliza(aplicacao, tmp_path):
    janela = JanelaPrincipal(tmp_path / "dados.baliza")
    janela.show()
    aplicacao.processEvents()

    assert janela.isVisible()
    assert janela.windowTitle() == "Baliza"
    assert janela.width() >= 1024
    janela.close()
