"""Peças de tela reaproveitadas, com os nomes do design system no Figma."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

ICONE_AVISO = {"erro": "⚠", "atencao": "⏱", "sucesso": "✓", "info": "ⓘ"}


def _repolir(widget: QWidget) -> None:
    widget.style().unpolish(widget)
    widget.style().polish(widget)


def texto(conteudo: str, papel: str = "", largura_maxima: int | None = None) -> QLabel:
    rotulo = QLabel(conteudo)
    if papel:
        rotulo.setProperty("papel", papel)
    rotulo.setWordWrap(True)
    if largura_maxima:
        rotulo.setMaximumWidth(largura_maxima)
    return rotulo


def botao(rotulo: str, tipo: str = "secundario") -> QPushButton:
    b = QPushButton(rotulo)
    b.setProperty("tipo", tipo)
    b.setCursor(Qt.CursorShape.PointingHandCursor)
    b.setAutoDefault(tipo == "principal")
    return b


def aviso(mensagem: str, tipo: str = "erro") -> QLabel:
    rotulo = QLabel(f"{ICONE_AVISO[tipo]}  {mensagem}")
    rotulo.setProperty("aviso", tipo)
    rotulo.setWordWrap(True)
    return rotulo


def mudar_aviso(rotulo: QLabel, mensagem: str, tipo: str) -> None:
    rotulo.setText(f"{ICONE_AVISO[tipo]}  {mensagem}")
    rotulo.setProperty("aviso", tipo)
    _repolir(rotulo)


def cartao() -> QFrame:
    quadro = QFrame()
    quadro.setObjectName("cartao")
    return quadro


def linha_de_acoes(*botoes: QPushButton, alinhar: str = "direita") -> QHBoxLayout:
    linha = QHBoxLayout()
    linha.setSpacing(12)
    if alinhar == "direita":
        linha.addStretch()
    for b in botoes:
        linha.addWidget(b)
    if alinhar == "esquerda":
        linha.addStretch()
    return linha


class Campo(QWidget):
    """Rótulo acima, caixa de texto e linha de ajuda ou de erro abaixo."""

    def __init__(self, rotulo: str, ajuda: str = "", senha: bool = False) -> None:
        super().__init__()
        self._ajuda = ajuda
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        self.rotulo = texto(rotulo, "rotulo")
        self.caixa = QLineEdit()
        self.rotulo.setBuddy(self.caixa)
        if senha:
            self.caixa.setEchoMode(QLineEdit.EchoMode.Password)
        self.linha_ajuda = texto(ajuda, "ajuda")
        self.linha_ajuda.setVisible(bool(ajuda))
        layout.addWidget(self.rotulo)
        layout.addWidget(self.caixa)
        layout.addWidget(self.linha_ajuda)
        self.caixa.textEdited.connect(lambda _: self.limpar_erro())

    def valor(self) -> str:
        return self.caixa.text()

    def definir(self, valor: str) -> None:
        self.caixa.setText(valor)

    def mostrar_erro(self, mensagem: str) -> None:
        self.caixa.setProperty("erro", True)
        _repolir(self.caixa)
        self.linha_ajuda.setText(f"⚠  {mensagem}")
        self.linha_ajuda.setProperty("papel", "erro")
        _repolir(self.linha_ajuda)
        self.linha_ajuda.setVisible(True)

    def limpar_erro(self) -> None:
        if not self.caixa.property("erro"):
            return
        self.caixa.setProperty("erro", False)
        _repolir(self.caixa)
        self.linha_ajuda.setText(self._ajuda)
        self.linha_ajuda.setProperty("papel", "ajuda")
        _repolir(self.linha_ajuda)
        self.linha_ajuda.setVisible(bool(self._ajuda))

    def tem_erro(self) -> bool:
        return bool(self.caixa.property("erro"))
