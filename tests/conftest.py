import os

import pytest

# Os testes de tela rodam sem janela visível, inclusive no GitHub Actions.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="session")
def aplicacao():
    from baliza.app import criar_aplicacao

    return criar_aplicacao([])
