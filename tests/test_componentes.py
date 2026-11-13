"""Listas de escolha: o texto das opções não sai cortado quando a lista abre."""

from PySide6.QtTest import QTest

LONGO = "015 · UBS BB CORRETORA DE CÂMBIO, TÍTULOS E VALORES MOBILIÁRIOS S.A."


def _campo(busca: bool):
    from econt.interface.componentes import CampoEscolha

    campo = CampoEscolha(
        "Banco", [("001", "001 · Banco do Brasil S.A."), ("015", LONGO)], busca=busca
    )
    campo.resize(260, 90)
    campo.show()
    return campo


def test_lista_aberta_tem_a_largura_do_texto(aplicacao):
    from econt.interface.componentes import LARGURA_MAXIMA_DA_LISTA

    for busca in (False, True):
        campo = _campo(busca)
        campo.caixa.showPopup()
        lista = campo.caixa.view()
        precisa = min(lista.sizeHintForColumn(0), LARGURA_MAXIMA_DA_LISTA - 60)
        assert lista.minimumWidth() > campo.caixa.width()
        assert lista.minimumWidth() >= precisa
        campo.caixa.hidePopup()


def test_sugestoes_tem_a_largura_do_texto(aplicacao):
    campo = _campo(busca=True)
    campo.caixa.setCurrentIndex(-1)
    campo.caixa.setEditText("")
    QTest.keyClicks(campo.caixa.lineEdit(), "corretora")
    assert campo.sugestoes() == [LONGO]
    popup = campo.caixa.completer().popup()
    assert popup.minimumWidth() > campo.caixa.width()
    assert popup.minimumWidth() >= popup.sizeHintForColumn(0)


def test_calendario_abre_sem_cortar_os_dias(aplicacao):
    from PySide6.QtCore import QCoreApplication
    from PySide6.QtGui import QShowEvent

    from econt.interface.componentes import CampoDataHora

    campo = CampoDataHora("Data e hora do pedido")
    calendario = campo.caixa.calendarWidget()
    QCoreApplication.sendEvent(calendario, QShowEvent())  # como quando o calendário abre
    assert calendario.minimumWidth() >= calendario.sizeHint().width()
    assert calendario.minimumHeight() >= calendario.sizeHint().height()
