"""Dados da entidade e logo: primeiro uso (T03) e área Entidade (T18)."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QBuffer, QByteArray, QIODevice, Qt, Signal
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QFileDialog, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from baliza.dados.entidade import Entidade, problemas_da_entidade
from baliza.dominio.documentos import formatar_cnpj
from baliza.interface.acesso import TelaCentral
from baliza.interface.componentes import (
    Abas,
    Campo,
    aviso,
    botao,
    cartao,
    linha_de_acoes,
    mudar_aviso,
    texto,
)
from baliza.interface.tema import CORES

TAMANHO_MAXIMO_ARQUIVO = 1024 * 1024
LADO_MAXIMO_LOGO = 256


class LogoInvalido(ValueError):
    pass


def preparar_logo(caminho: str | Path) -> bytes:
    """Lê PNG ou JPG de até 1 MB e guarda como PNG de no máximo 256 px."""
    caminho = Path(caminho)
    if caminho.stat().st_size > TAMANHO_MAXIMO_ARQUIVO:
        raise LogoInvalido("O logo precisa ter até 1 MB.")
    imagem = QImage(str(caminho))
    if imagem.isNull():
        raise LogoInvalido("Não foi possível abrir a imagem. Use um arquivo PNG ou JPG.")
    if max(imagem.width(), imagem.height()) > LADO_MAXIMO_LOGO:
        imagem = imagem.scaled(
            LADO_MAXIMO_LOGO,
            LADO_MAXIMO_LOGO,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
    dados = QByteArray()
    buffer = QBuffer(dados)
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    imagem.save(buffer, "PNG")
    return bytes(dados.data())


def pixmap_do_logo(logo: bytes | None, lado: int) -> QPixmap:
    imagem = QPixmap()
    if logo:
        imagem.loadFromData(logo)
    if imagem.isNull():
        return QPixmap()
    return imagem.scaled(
        lado, lado, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
    )


class FormularioEntidade(QWidget):
    """Razão social, CNPJ e logo, com validação ao salvar."""

    def __init__(self, entidade: Entidade | None = None) -> None:
        super().__init__()
        self.logo: bytes | None = entidade.logo if entidade else None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        self.razao_social = Campo("Razão social")
        self.cnpj = Campo("CNPJ", "Formato: 00.000.000/0000-00")
        if entidade:
            self.razao_social.definir(entidade.razao_social)
            self.cnpj.definir(entidade.cnpj_formatado)
        self.cnpj.caixa.editingFinished.connect(self._formatar_cnpj)
        layout.addWidget(self.razao_social)
        layout.addWidget(self.cnpj)

        linha = QHBoxLayout()
        linha.setSpacing(16)
        self.previa = QLabel()
        self.previa.setFixedSize(56, 56)
        self.previa.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.previa.setStyleSheet(
            f"background: {CORES['bg/window']}; border: 1px dashed {CORES['border/input']};"
            "border-radius: 8px;"
        )
        coluna = QVBoxLayout()
        coluna.setSpacing(4)
        self.escolher = botao("Escolher logo")
        self.remover = botao("Tirar logo", "link")
        coluna.addLayout(linha_de_acoes(self.escolher, self.remover, alinhar="esquerda"))
        self.ajuda_logo = texto("PNG ou JPG, até 1 MB. Opcional.", "ajuda")
        coluna.addWidget(self.ajuda_logo)
        linha.addWidget(self.previa)
        linha.addLayout(coluna, 1)
        layout.addLayout(linha)
        self.escolher.clicked.connect(self._escolher_logo)
        self.remover.clicked.connect(lambda: self.definir_logo(None))
        self._atualizar_previa()

    def _formatar_cnpj(self) -> None:
        self.cnpj.definir(formatar_cnpj(self.cnpj.valor()))

    def _escolher_logo(self) -> None:
        caminho, _ = QFileDialog.getOpenFileName(
            self, "Escolher o logo", str(Path.home()), "Imagens (*.png *.jpg *.jpeg)"
        )
        if caminho:
            self.carregar_logo(caminho)

    def carregar_logo(self, caminho: str | Path) -> bool:
        try:
            self.definir_logo(preparar_logo(caminho))
        except LogoInvalido as erro:
            self.ajuda_logo.setText(f"⚠  {erro}")
            self.ajuda_logo.setProperty("papel", "erro")
            self.ajuda_logo.style().polish(self.ajuda_logo)
            return False
        return True

    def definir_logo(self, logo: bytes | None) -> None:
        self.logo = logo
        self.ajuda_logo.setText("PNG ou JPG, até 1 MB. Opcional.")
        self.ajuda_logo.setProperty("papel", "ajuda")
        self.ajuda_logo.style().polish(self.ajuda_logo)
        self._atualizar_previa()

    def _atualizar_previa(self) -> None:
        self.previa.setPixmap(pixmap_do_logo(self.logo, 48))
        self.escolher.setText("Trocar logo" if self.logo else "Escolher logo")
        self.remover.setVisible(bool(self.logo))

    def entidade_validada(self) -> Entidade | None:
        """Mostra os erros nos campos e devolve a entidade só quando está tudo certo."""
        erros = problemas_da_entidade(self.razao_social.valor(), self.cnpj.valor())
        for chave, campo in (("razao_social", self.razao_social), ("cnpj", self.cnpj)):
            if chave in erros:
                campo.mostrar_erro(erros[chave])
            else:
                campo.limpar_erro()
        if erros:
            (self.razao_social if "razao_social" in erros else self.cnpj).caixa.setFocus()
            return None
        return Entidade(self.razao_social.valor().strip(), self.cnpj.valor(), self.logo)


class TelaDadosEntidade(TelaCentral):
    """T03 · Dados da entidade no primeiro uso."""

    salva = Signal(object)

    def __init__(self) -> None:
        super().__init__()
        self.adicionar(texto("Dados da entidade", "titulo"))
        self.adicionar(
            texto("A entidade é quem paga. O Baliza cadastra uma única entidade.", "apoio")
        )
        self.formulario = FormularioEntidade()
        self.adicionar(self.formulario)
        self.salvar = botao("Salvar e continuar", "principal")
        self.adicionar(linha_de_acoes(self.salvar))
        self.salvar.clicked.connect(self._salvar)

    def _salvar(self) -> None:
        entidade = self.formulario.entidade_validada()
        if entidade:
            self.salva.emit(entidade)


class PaginaEntidade(QWidget):
    """Área Entidade: aba Dados (T18) e, quando houver base aberta, aba Contas (T19 a T21)."""

    salva = Signal(object)

    def __init__(self, entidade: Entidade | None, contas: QWidget | None = None) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 32, 40, 32)
        layout.setSpacing(16)
        layout.addWidget(texto("Entidade", "titulo"))
        self.abas = Abas()
        layout.addWidget(self.abas, 1)

        dados = QWidget()
        coluna = QVBoxLayout(dados)
        coluna.setContentsMargins(0, 20, 0, 0)
        coluna.setSpacing(20)
        self.retorno = aviso("", "sucesso")
        self.retorno.setVisible(False)
        self.retorno.setMaximumWidth(720)
        coluna.addWidget(self.retorno)
        quadro = cartao()
        quadro.setMaximumWidth(720)
        interno = QVBoxLayout(quadro)
        interno.setContentsMargins(24, 20, 24, 20)
        self.formulario = FormularioEntidade(entidade)
        interno.addWidget(self.formulario)
        interno.addWidget(texto("O Baliza cadastra uma única entidade.", "ajuda"))
        coluna.addWidget(quadro)
        self.salvar = botao("Salvar", "principal")
        acoes = linha_de_acoes(self.salvar)
        acoes.setContentsMargins(0, 0, 0, 0)
        largura = QWidget()
        largura.setMaximumWidth(720)
        largura.setLayout(acoes)
        coluna.addWidget(largura)
        coluna.addStretch()
        self.abas.addTab(dados, "Dados")
        self.contas = contas
        if contas is not None:
            self.abas.addTab(contas, "Contas")
        self.salvar.clicked.connect(self._salvar)

    def _salvar(self) -> None:
        entidade = self.formulario.entidade_validada()
        if entidade:
            self.salva.emit(entidade)
            mudar_aviso(self.retorno, "Dados da entidade salvos.", "sucesso")
            self.retorno.setVisible(True)
