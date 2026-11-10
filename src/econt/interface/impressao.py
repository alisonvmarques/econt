"""Impressões do ECont, feitas com QTextDocument (tamanho A4)."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from html import escape
from pathlib import Path

from PySide6.QtCore import QMarginsF, QPointF, QRectF, QSizeF, Qt, QUrl
from PySide6.QtGui import (
    QColor,
    QImage,
    QPageLayout,
    QPageSize,
    QPainter,
    QPdfWriter,
    QPen,
    QTextDocument,
)
from PySide6.QtPrintSupport import QPrintDialog, QPrinter, QPrintPreviewWidget
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from econt.interface.tema import CORES

URL_LOGO = QUrl("econt://logo")


def _cabecalho(nome_entidade: str | None, cnpj: str | None, assunto: str, com_logo: bool) -> str:
    logo = f'<img src="{URL_LOGO.toString()}" height="40">' if com_logo else ""
    nome = escape(nome_entidade or "")
    doc = escape(cnpj or "")
    return f"""
    <table width="100%" style="border-bottom: 1px solid {CORES["border/input"]};">
      <tr>
        <td width="48">{logo}</td>
        <td><b style="font-size: 11pt;">{nome}</b><br>
            <span style="font-size: 8pt; color: {CORES["text/secondary"]};">{doc}</span></td>
        <td align="right" style="font-size: 8pt; color: {CORES["text/secondary"]};">{assunto}</td>
      </tr>
    </table>"""


def html_chave_recuperacao(
    chave: str,
    gerada_em: datetime,
    nome_entidade: str | None = None,
    cnpj: str | None = None,
    com_logo: bool = False,
) -> str:
    """I03 · Chave de recuperação, em A4."""
    quando = gerada_em.strftime("%d/%m/%Y às %H:%M")
    return f"""
    <html><body style="font-size: 10pt; color: {CORES["text/primary"]};">
    {_cabecalho(nome_entidade, cnpj, "Chave de recuperação", com_logo)}
    <h2 style="font-size: 14pt;">Chave de recuperação do ECont</h2>
    <p>Use esta chave para criar uma senha nova se esquecer a senha. Sem a senha e sem esta chave,
    os dados não podem ser abertos por ninguém.</p>
    <table width="100%" cellpadding="18" style="border: 1.5px solid {CORES["text/primary"]};">
      <tr><td align="center"><span style="font-size: 20pt; font-weight: 600;">{escape(chave)}</span>
      <br><span style="font-size: 8pt; color: {CORES["text/secondary"]};">Letras maiúsculas e
      números, sem as letras I e O e sem os números 0 e 1, para não confundir.</span></td></tr>
    </table>
    <h3 style="font-size: 11pt;">Como guardar</h3>
    <p>• Guarde esta folha em lugar seguro, longe do computador.<br>
       • Não envie a chave por e-mail nem por mensagem.<br>
       • Gerar uma chave nova invalida esta.</p>
    <p style="font-size: 8pt; color: {CORES["text/secondary"]};">
       Emitido pelo ECont em {quando}</p>
    </body></html>"""


def documento(html: str, logo: bytes | None = None) -> QTextDocument:
    doc = QTextDocument()
    if logo:
        doc.addResource(QTextDocument.ResourceType.ImageResource, URL_LOGO, QImage.fromData(logo))
    doc.setHtml(html)
    return doc


def _pagina_a4() -> QPageLayout:
    return QPageLayout(
        QPageSize(QPageSize.PageSizeId.A4),
        QPageLayout.Orientation.Portrait,
        QMarginsF(18, 16, 18, 16),
        QPageLayout.Unit.Millimeter,
    )


def salvar_pdf(html: str, caminho: str, logo: bytes | None = None) -> None:
    escritor = QPdfWriter(caminho)
    escritor.setPageLayout(_pagina_a4())
    escritor.setResolution(300)
    escritor.setTitle("ECont")
    doc = documento(html, logo)
    doc.setPageSize(QSizeF(escritor.width(), escritor.height()))
    doc.print_(escritor)


def imprimir(html: str, janela: QWidget, logo: bytes | None = None) -> bool:
    """Abre a janela de impressão do sistema. Devolve True se a pessoa imprimiu."""
    impressora = QPrinter(QPrinter.PrinterMode.HighResolution)
    impressora.setPageLayout(_pagina_a4())
    dialogo = QPrintDialog(impressora, janela)
    if dialogo.exec() != QPrintDialog.DialogCode.Accepted:
        return False
    documento(html, logo).print_(impressora)
    return True


# Impressões desenhadas página a página -------------------------------------------------------
#
# A meia folha precisa da linha de corte exatamente no meio da A4, e a ficha completa precisa
# de rodapé com "Página x de y". Por isso essas impressões são desenhadas com QPainter numa
# página A4 inteira, sem as margens da impressora, e cada uma cuida das próprias margens.


def mm(milimetros: float, dispositivo) -> float:
    return milimetros * dispositivo.logicalDpiY() / 25.4


def emitido(quando: datetime) -> str:
    return f"Emitido pelo ECont em {quando.strftime('%d/%m/%Y às %H:%M')}"


def _documento_no(dispositivo, html: str, logo: bytes | None, largura: float) -> QTextDocument:
    doc = documento(html, logo)
    doc.documentLayout().setPaintDevice(dispositivo)
    doc.setTextWidth(largura)
    return doc


def _rodape(esquerda: str, direita: str) -> str:
    cor = CORES["text/secondary"]
    return (
        f'<table width="100%" style="font-size: 7.5pt; color: {cor};"><tr>'
        f'<td>{escape(esquerda)}</td><td align="right">{escape(direita)}</td></tr></table>'
    )


class Impressao:
    """Algo que se desenha em páginas A4. `nova_pagina` avança para a próxima folha."""

    titulo = "ECont"
    nome_do_arquivo = "econt.pdf"

    def desenhar(self, pintor: QPainter, dispositivo, nova_pagina: Callable[[], object]) -> None:
        raise NotImplementedError

    def paginas(self, dispositivo) -> int:
        return 1


class DadosParaPagamento(Impressao):
    """I01 · Meia folha: até dois blocos numa A4, com a linha de corte no meio (RF05).

    Com um bloco só, a metade de baixo fica em branco: serve para a folha completa com um
    fornecedor e para a meia folha avulsa, que já vai cortada para a impressora (RF19).
    """

    titulo = "Dados para pagamento"

    def __init__(self, blocos: list[str], logo: bytes | None, quando: datetime) -> None:
        if not 1 <= len(blocos) <= 2:
            raise ValueError("A meia folha leva um ou dois fornecedores.")
        self.blocos = blocos
        self.logo = logo
        self.quando = quando
        self.nome_do_arquivo = f"dados-para-pagamento-{quando:%Y%m%d-%H%M}.pdf"

    def desenhar(self, pintor, dispositivo, nova_pagina) -> None:
        largura, altura = dispositivo.width(), dispositivo.height()
        metade = altura / 2
        lado, topo, base = mm(15, dispositivo), mm(12, dispositivo), mm(9, dispositivo)
        util = largura - 2 * lado
        for numero, bloco in enumerate(self.blocos):
            inicio = numero * metade
            rodape = _documento_no(
                dispositivo, _rodape(emitido(self.quando), "Conferir antes de pagar"), None, util
            )
            y_rodape = inicio + metade - base - rodape.size().height()
            conteudo = _documento_no(dispositivo, bloco, self.logo, util)
            espaco = y_rodape - (inicio + topo) - mm(3, dispositivo)
            escala = min(1.0, espaco / conteudo.size().height())
            pintor.save()
            pintor.translate(lado, inicio + topo)
            pintor.scale(escala, escala)
            conteudo.drawContents(pintor, QRectF(0, 0, util / escala, espaco / escala))
            pintor.restore()
            pintor.save()
            pintor.translate(lado, y_rodape)
            rodape.drawContents(pintor)
            pintor.restore()
        # Linha de corte no meio exato da folha.
        caneta = QPen(QColor(CORES["border/input"]))
        caneta.setStyle(Qt.PenStyle.DashLine)
        caneta.setWidthF(mm(0.25, dispositivo))
        pintor.setPen(caneta)
        rotulo = _documento_no(
            dispositivo,
            f'<span style="font-size: 7pt; color: {CORES["text/secondary"]};">corte aqui</span>',
            None,
            mm(30, dispositivo),
        )
        largura_rotulo = rotulo.idealWidth()
        pintor.drawLine(
            QPointF(mm(5, dispositivo) + largura_rotulo + mm(2, dispositivo), metade),
            QPointF(largura, metade),
        )
        pintor.save()
        pintor.translate(mm(5, dispositivo), metade - rotulo.size().height() / 2)
        rotulo.drawContents(pintor)
        pintor.restore()


class Paginada(Impressao):
    """I02 · Documento A4 com quebra de página e rodapé "Página x de y"."""

    def __init__(
        self, html: str, logo: bytes | None, quando: datetime, titulo: str, nome_do_arquivo: str
    ) -> None:
        self.html = html
        self.logo = logo
        self.quando = quando
        self.titulo = titulo
        self.nome_do_arquivo = nome_do_arquivo

    def _medidas(self, dispositivo):
        lado, topo, base = mm(18, dispositivo), mm(16, dispositivo), mm(14, dispositivo)
        largura = dispositivo.width() - 2 * lado
        altura = dispositivo.height() - topo - base - mm(8, dispositivo)
        doc = _documento_no(dispositivo, self.html, self.logo, largura)
        doc.setPageSize(QSizeF(largura, altura))
        return doc, lado, topo, base, largura, altura

    def paginas(self, dispositivo) -> int:
        return self._medidas(dispositivo)[0].pageCount()

    def desenhar(self, pintor, dispositivo, nova_pagina) -> None:
        doc, lado, topo, base, largura, altura = self._medidas(dispositivo)
        total = doc.pageCount()
        for pagina in range(total):
            if pagina:
                nova_pagina()
            pintor.save()
            pintor.translate(lado, topo - pagina * altura)
            doc.drawContents(pintor, QRectF(0, pagina * altura, largura, altura))
            pintor.restore()
            rodape = _documento_no(
                dispositivo,
                _rodape(emitido(self.quando), f"Página {pagina + 1} de {total}"),
                None,
                largura,
            )
            pintor.save()
            pintor.translate(lado, dispositivo.height() - base - rodape.size().height())
            rodape.drawContents(pintor)
            pintor.restore()


def salvar_pdf_impressao(impressao: Impressao, caminho: str) -> None:
    escritor = QPdfWriter(caminho)
    escritor.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
    escritor.setPageMargins(QMarginsF(0, 0, 0, 0))
    escritor.setResolution(300)
    escritor.setTitle(impressao.titulo)
    escritor.setCreator("ECont")
    pintor = QPainter(escritor)
    impressao.desenhar(pintor, escritor, escritor.newPage)
    pintor.end()


def nova_impressora() -> QPrinter:
    impressora = QPrinter(QPrinter.PrinterMode.HighResolution)
    impressora.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
    impressora.setFullPage(True)
    impressora.setPageMargins(QMarginsF(0, 0, 0, 0), QPageLayout.Unit.Millimeter)
    return impressora


def pintar_na_impressora(impressao: Impressao, impressora: QPrinter) -> None:
    pintor = QPainter(impressora)
    impressao.desenhar(pintor, impressora, impressora.newPage)
    pintor.end()


class JanelaImpressao(QDialog):
    """Pré-visualização antes de imprimir, com Imprimir e Salvar em PDF."""

    def __init__(self, pai: QWidget | None, impressao: Impressao) -> None:
        super().__init__(pai)
        self.impressao = impressao
        self.setWindowTitle(impressao.titulo)
        self.setObjectName("dialogo")
        self.resize(760, 860)
        self.impressora = nova_impressora()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        self.previa = QPrintPreviewWidget(self.impressora, self)
        self.previa.paintRequested.connect(lambda p: pintar_na_impressora(impressao, p))
        self.previa.fitToWidth()
        layout.addWidget(self.previa, 1)
        self.retorno = QLabel("")
        self.retorno.setProperty("papel", "ajuda")
        layout.addWidget(self.retorno)
        linha = QHBoxLayout()
        self.salvar = QPushButton("Salvar em PDF")
        self.imprimir = QPushButton("Imprimir…")
        self.imprimir.setProperty("tipo", "principal")
        self.fechar = QPushButton("Fechar")
        linha.addWidget(self.salvar)
        linha.addStretch()
        linha.addWidget(self.fechar)
        linha.addWidget(self.imprimir)
        layout.addLayout(linha)
        self.salvar.clicked.connect(self._salvar)
        self.imprimir.clicked.connect(self._imprimir)
        self.fechar.clicked.connect(self.reject)
        self.impresso = False

    def escolher_arquivo(self) -> str:
        caminho, _ = QFileDialog.getSaveFileName(
            self,
            "Salvar em PDF",
            str(Path.home() / self.impressao.nome_do_arquivo),
            "PDF (*.pdf)",
        )
        return caminho

    def _salvar(self) -> None:
        caminho = self.escolher_arquivo()
        if not caminho:
            return
        if not caminho.lower().endswith(".pdf"):
            caminho += ".pdf"
        salvar_pdf_impressao(self.impressao, caminho)
        self.impresso = True
        self.retorno.setText(f"✓  Salvo em {caminho}")

    def _imprimir(self) -> None:
        dialogo = QPrintDialog(self.impressora, self)
        if dialogo.exec() == QPrintDialog.DialogCode.Accepted:
            pintar_na_impressora(self.impressao, self.impressora)
            self.impresso = True
            self.accept()


def abrir_janela_impressao(pai: QWidget | None, impressao: Impressao) -> bool:
    """Pré-visualização com Imprimir e Salvar em PDF. Devolve True se imprimiu ou salvou."""
    janela = JanelaImpressao(pai, impressao)
    janela.exec()
    return janela.impresso
