"""Ícones do ECont (traço de 1,4 px em grade de 16 px), os mesmos do Figma."""

from PySide6.QtCore import QByteArray
from PySide6.QtGui import QIcon, QPixmap

_TRACO = 'stroke="{cor}" stroke-width="1.4" fill="none" stroke-linecap="round"'
CAMINHOS = {
    "inicio": '<path d="M2.5 7.5L8 3l5.5 4.5V13a.5.5 0 01-.5.5H3a.5.5 0 01-.5-.5z" {t}/>',
    "consulta": '<circle cx="7" cy="7" r="4.5" {t}/><path d="M10.5 10.5L14 14" {t}/>',
    "fornecedores": (
        '<circle cx="6" cy="5.5" r="2.5" {t}/>'
        '<path d="M1.5 13.5c.5-2.5 2.3-3.5 4.5-3.5s4 1 4.5 3.5M11 3.5a2.5 2.5 0 010 5'
        'M12.5 10.5c1 .5 1.8 1.5 2 3" {t}/>'
    ),
    "entidade": '<path d="M2 6l6-3.5L14 6M3 6.5v6M6.3 6.5v6M9.7 6.5v6M13 6.5v6M2 13.5h12" {t}/>',
    "configuracoes": (
        '<circle cx="8" cy="8" r="2.2" {t}/>'
        '<path d="M8 1.8v2M8 12.2v2M1.8 8h2M12.2 8h2M3.6 3.6l1.4 1.4M11 11l1.4 1.4'
        'M3.6 12.4L5 11M11 5l1.4-1.4" {t}/>'
    ),
}


def icone(nome: str, cor: str, tamanho: int = 16) -> QIcon:
    corpo = CAMINHOS[nome].replace("{t}", _TRACO).replace("{cor}", cor)
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{tamanho}" height="{tamanho}" '
        f'viewBox="0 0 16 16">{corpo}</svg>'
    )
    imagem = QPixmap()
    imagem.loadFromData(QByteArray(svg.encode("utf-8")), "SVG")
    return QIcon(imagem)
