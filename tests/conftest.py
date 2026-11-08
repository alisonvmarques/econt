import gc
import os

import pytest

# Os testes de tela rodam sem janela visível, inclusive no GitHub Actions.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="session")
def _aplicacao_da_sessao():
    from baliza.app import criar_aplicacao

    return criar_aplicacao([])


@pytest.fixture
def aplicacao(_aplicacao_da_sessao):
    """Aplicação Qt dos testes de tela. Ao fim de cada teste, as janelas criadas por ele são
    destruídas enquanto o Qt ainda está de pé, para o encerramento não cair numa ordem
    errada de destruição."""
    from PySide6.QtCore import QCoreApplication, QEvent
    from PySide6.QtWidgets import QApplication

    yield _aplicacao_da_sessao
    for janela in QApplication.topLevelWidgets():
        janela.close()
        janela.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    gc.collect()
