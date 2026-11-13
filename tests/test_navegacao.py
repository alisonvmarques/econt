from PySide6.QtCore import Qt
from PySide6.QtTest import QTest

from econt.interface.area_principal import AREAS, AreaPrincipal


def test_seis_areas_e_inicio_destacado(aplicacao):
    area = AreaPrincipal()
    assert [b.text() for b in area.navegacao.botoes.values()] == [r for _, r in AREAS]
    assert [r for _, r in AREAS] == [
        "Início",
        "Consulta",
        "Fornecedores",
        "Entidade",
        "Atividades",
        "Configurações",
    ]
    assert area.area_atual() == "inicio"
    assert area.navegacao.botoes["inicio"].isChecked()


def test_clique_troca_de_area_e_destaca(aplicacao):
    area = AreaPrincipal()
    area.navegacao.botoes["entidade"].click()
    assert area.area_atual() == "entidade"
    assert area.navegacao.botoes["entidade"].isChecked()
    assert not area.navegacao.botoes["inicio"].isChecked()


def test_navegacao_pelo_teclado(aplicacao):
    area = AreaPrincipal()
    area.show()
    area.activateWindow()
    QTest.qWaitForWindowActive(area)
    area.navegacao.botoes["inicio"].setFocus()
    QTest.keyClick(area.navegacao.botoes["inicio"], Qt.Key.Key_Down)
    assert area.area_atual() == "consulta"
    QTest.keyClick(area.navegacao.botoes["consulta"], Qt.Key.Key_Up)
    assert area.area_atual() == "inicio"
    QTest.keyClick(
        area.navegacao.botoes["inicio"], Qt.Key.Key_3, Qt.KeyboardModifier.ControlModifier
    )
    assert area.area_atual() == "fornecedores"
    QTest.keyClick(
        area.navegacao.botoes["fornecedores"], Qt.Key.Key_5, Qt.KeyboardModifier.ControlModifier
    )
    assert area.area_atual() == "atividades"
    QTest.keyClick(
        area.navegacao.botoes["atividades"], Qt.Key.Key_6, Qt.KeyboardModifier.ControlModifier
    )
    assert area.area_atual() == "configuracoes"
    assert area.navegacao.botoes["configuracoes"].toolTip() == "Configurações (Ctrl+6)"
    area.close()
