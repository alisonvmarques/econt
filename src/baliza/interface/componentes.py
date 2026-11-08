"""Peças de tela reaproveitadas, com os nomes do design system no Figma."""

from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import QDateTime, Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QCompleter,
    QDateTimeEdit,
    QDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
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


class CampoBase(QWidget):
    """Rótulo acima, o controle e uma linha de ajuda ou de erro abaixo."""

    def __init__(self, rotulo: str, controle: QWidget, ajuda: str = "") -> None:
        super().__init__()
        self._ajuda = ajuda
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        self.rotulo = texto(rotulo, "rotulo")
        self.caixa = controle
        self.rotulo.setBuddy(controle)
        controle.setAccessibleName(rotulo)
        self.linha_ajuda = texto(ajuda, "ajuda")
        self.linha_ajuda.setVisible(bool(ajuda))
        layout.addWidget(self.rotulo)
        layout.addWidget(controle)
        layout.addWidget(self.linha_ajuda)

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

    def definir_ajuda(self, ajuda: str) -> None:
        """Troca a linha de ajuda; um erro à mostra continua até ser corrigido."""
        self._ajuda = ajuda
        if not self.tem_erro():
            self.linha_ajuda.setText(ajuda)
            self.linha_ajuda.setVisible(bool(ajuda))


class Campo(CampoBase):
    """Campo de texto."""

    def __init__(self, rotulo: str, ajuda: str = "", senha: bool = False) -> None:
        super().__init__(rotulo, QLineEdit(), ajuda)
        if senha:
            self.caixa.setEchoMode(QLineEdit.EchoMode.Password)
        self.caixa.textEdited.connect(lambda _: self.limpar_erro())

    def valor(self) -> str:
        return self.caixa.text()

    def definir(self, valor: str) -> None:
        self.caixa.setText(valor)


class CampoEscolha(CampoBase):
    """Lista de escolha. Com `busca=True`, dá para digitar parte do texto para filtrar."""

    def __init__(
        self, rotulo: str, opcoes: list[tuple[str, str]], ajuda: str = "", busca: bool = False
    ) -> None:
        super().__init__(rotulo, QComboBox(), ajuda)
        for chave, rotulo_opcao in opcoes:
            self.caixa.addItem(rotulo_opcao, chave)
        # A largura vem do layout, não do nome mais longo da lista (há bancos com nomes enormes).
        self.caixa.setSizeAdjustPolicy(
            QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
        )
        self.caixa.setMinimumContentsLength(12)
        if busca:
            self.caixa.setEditable(True)
            self.caixa.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
            completar = self.caixa.completer()
            completar.setFilterMode(Qt.MatchFlag.MatchContains)
            completar.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
            self.caixa.lineEdit().setPlaceholderText("Digite o código ou o nome")
        self.caixa.currentIndexChanged.connect(lambda _: self.limpar_erro())

    def valor(self) -> str:
        """A chave da opção escolhida, ou vazio quando o texto digitado não é uma opção."""
        indice = self.caixa.currentIndex()
        if indice < 0 or (
            self.caixa.isEditable() and self.caixa.currentText() != self.caixa.itemText(indice)
        ):
            return ""
        return self.caixa.itemData(indice)

    def definir(self, chave: str) -> None:
        self.caixa.setCurrentIndex(self.caixa.findData(chave))


class CampoDataHora(CampoBase):
    def __init__(self, rotulo: str, ajuda: str = "") -> None:
        controle = QDateTimeEdit(QDateTime.currentDateTime())
        controle.setDisplayFormat("dd/MM/yyyy HH:mm")
        controle.setCalendarPopup(True)
        super().__init__(rotulo, controle, ajuda)
        controle.dateTimeChanged.connect(lambda _: self.limpar_erro())

    def valor(self) -> datetime:
        return self.caixa.dateTime().toPython().replace(second=0, microsecond=0)

    def definir(self, momento: datetime) -> None:
        self.caixa.setDateTime(QDateTime(momento))


def perguntar(pai: QWidget, titulo: str, mensagem: str, confirmar: str) -> bool:
    """Confirmação antes de uma ação importante (RNF03). Cancelar é o padrão."""
    caixa = QMessageBox(pai)
    caixa.setWindowTitle(titulo)
    caixa.setText(mensagem)
    sim = caixa.addButton(confirmar, QMessageBox.ButtonRole.AcceptRole)
    nao = caixa.addButton("Cancelar", QMessageBox.ButtonRole.RejectRole)
    caixa.setDefaultButton(nao)
    caixa.exec()
    return caixa.clickedButton() is sim


class Dialogo(QDialog):
    """Janela por cima da tela, com título, corpo e botões Cancelar e confirmar."""

    def __init__(self, pai: QWidget | None, titulo: str, confirmar: str) -> None:
        super().__init__(pai)
        self.setWindowTitle(titulo)
        self.setObjectName("dialogo")
        self.setMinimumWidth(520)
        self.corpo = QVBoxLayout(self)
        self.corpo.setContentsMargins(24, 20, 24, 20)
        self.corpo.setSpacing(16)
        self.corpo.addWidget(texto(titulo, "secao"))
        self.cancelar = botao("Cancelar")
        self.confirmar = botao(confirmar, "principal")
        self.cancelar.clicked.connect(self.reject)
        self.confirmar.clicked.connect(self.ao_confirmar)

    def showEvent(self, evento) -> None:  # noqa: N802 (nome do Qt)
        # Altura calculada para a largura real: textos que quebram linha não se sobrepõem
        # aos campos.
        largura = max(self.minimumWidth(), self.width())
        altura = self.layout().totalHeightForWidth(largura)
        if altura > 0:
            self.resize(largura, max(altura, self.layout().minimumSize().height()))
        super().showEvent(evento)

    def fechar_corpo(self) -> None:
        """Chame depois de acrescentar os campos: põe os botões no fim."""
        self.corpo.addLayout(linha_de_acoes(self.cancelar, self.confirmar))

    def ao_confirmar(self) -> None:
        self.accept()


class Tabela(QTableWidget):
    """Tabela só de leitura, linha inteira selecionável, com os nomes de coluna do Figma.

    `escolhida` avisa a linha escolhida com clique ou com Enter (RNF05).
    """

    escolhida = Signal(int)

    def __init__(self, colunas: list[str]) -> None:
        super().__init__(0, len(colunas))
        self.setHorizontalHeaderLabels(colunas)
        self.verticalHeader().setVisible(False)
        self.setShowGrid(False)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setWordWrap(True)
        cabecalho = self.horizontalHeader()
        cabecalho.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        cabecalho.setHighlightSections(False)
        self.cellClicked.connect(lambda linha, _: self.escolhida.emit(linha))

    def keyPressEvent(self, evento) -> None:  # noqa: N802 (nome do Qt)
        if evento.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and self.currentRow() >= 0:
            self.escolhida.emit(self.currentRow())
            return
        super().keyPressEvent(evento)

    def celula(self, linha: int, coluna: int, valor: str, dado: object = None) -> None:
        item = QTableWidgetItem(valor)
        if dado is not None:
            item.setData(Qt.ItemDataRole.UserRole, dado)
        self.setItem(linha, coluna, item)

    def ajustar(self) -> None:
        """Depois de preencher: altura das linhas e largura das colunas com etiquetas.

        O Qt não conta as peças postas nas células ao medir a coluna, então a largura
        mínima delas é aplicada à mão.
        """
        self.resizeRowsToContents()
        cabecalho = self.horizontalHeader()
        for coluna in range(self.columnCount()):
            larguras = [
                w.minimumWidth()
                for linha in range(self.rowCount())
                if (w := self.cellWidget(linha, coluna)) is not None
            ]
            if not larguras:
                continue
            largura = max([*larguras, cabecalho.sectionSizeHint(coluna)])
            if cabecalho.sectionResizeMode(coluna) != QHeaderView.ResizeMode.Stretch:
                cabecalho.setSectionResizeMode(coluna, QHeaderView.ResizeMode.Fixed)
                cabecalho.resizeSection(coluna, largura + 8)

    def dado_da_linha(self, linha: int) -> object:
        item = self.item(linha, 0)
        return item.data(Qt.ItemDataRole.UserRole) if item else None


def etiqueta(rotulo: str, tipo: str = "neutra") -> QLabel:
    """Etiqueta de situação. O texto diz a situação; a cor só reforça (RNF15)."""
    marca = QLabel(rotulo)
    marca.setProperty("etiqueta", tipo)
    marca.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
    return marca


def empilhar(*widgets: QWidget, margem: int = 8) -> QWidget:
    """Junta peças uma embaixo da outra, para pôr numa célula de tabela."""
    caixa = QWidget()
    layout = QVBoxLayout(caixa)
    layout.setContentsMargins(margem, 6, margem, 6)
    layout.setSpacing(4)
    layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
    for w in widgets:
        layout.addWidget(w, 0, Qt.AlignmentFlag.AlignLeft)
        w.ensurePolished()
    # Polido antes de entrar na tabela, o tamanho já conta com as margens do tema; assim a
    # tabela reserva altura e largura suficientes e a etiqueta não sai cortada.
    caixa.ensurePolished()
    caixa.setMinimumSize(caixa.sizeHint())
    return caixa


class Abas(QTabWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setDocumentMode(True)
        self.tabBar().setDrawBase(False)
