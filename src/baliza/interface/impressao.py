"""Impressões do Baliza, feitas com QTextDocument (tamanho A4)."""

from __future__ import annotations

from datetime import datetime
from html import escape

from PySide6.QtCore import QMarginsF, QSizeF, QUrl
from PySide6.QtGui import QImage, QPageLayout, QPageSize, QPdfWriter, QTextDocument
from PySide6.QtPrintSupport import QPrintDialog, QPrinter
from PySide6.QtWidgets import QWidget

from baliza.interface.tema import CORES

URL_LOGO = QUrl("baliza://logo")


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
    <h2 style="font-size: 14pt;">Chave de recuperação do Baliza</h2>
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
       Emitido pelo Baliza em {quando}</p>
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
    escritor.setTitle("Baliza")
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
