"""Ponto de entrada do Baliza."""

import sys

from PySide6.QtWidgets import QApplication

from baliza import __version__
from baliza.interface.janela_principal import JanelaPrincipal


def criar_aplicacao(argumentos: list[str] | None = None) -> QApplication:
    aplicacao = QApplication.instance() or QApplication(argumentos or sys.argv)
    aplicacao.setApplicationName("Baliza")
    aplicacao.setApplicationVersion(__version__)
    return aplicacao


def main() -> int:
    aplicacao = criar_aplicacao()
    janela = JanelaPrincipal()
    janela.show()
    return aplicacao.exec()


if __name__ == "__main__":
    sys.exit(main())
