"""Janela principal do Baliza."""

from PySide6.QtWidgets import QMainWindow, QWidget

TITULO = "Baliza"
LARGURA_INICIAL, ALTURA_INICIAL = 1280, 800
LARGURA_MINIMA, ALTURA_MINIMA = 1024, 640


class JanelaPrincipal(QMainWindow):
    """Janela que vai receber a navegação lateral e as áreas do sistema."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(TITULO)
        self.resize(LARGURA_INICIAL, ALTURA_INICIAL)
        self.setMinimumSize(LARGURA_MINIMA, ALTURA_MINIMA)
        conteudo = QWidget(self)
        conteudo.setObjectName("conteudo")
        conteudo.setStyleSheet("#conteudo { background-color: #E9EAE6; }")
        self.setCentralWidget(conteudo)
