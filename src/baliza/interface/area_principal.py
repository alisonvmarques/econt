"""Área principal: navegação lateral (T06) e as áreas do sistema."""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from baliza.dados.banco import BaseDeDados
from baliza.dados.entidade import Entidade, obter_entidade, salvar_entidade
from baliza.interface.componentes import texto
from baliza.interface.configuracoes import PaginaConfiguracoes
from baliza.interface.consulta import PaginaConsulta
from baliza.interface.contas import PaginaContas
from baliza.interface.entidade import PaginaEntidade, pixmap_do_logo
from baliza.interface.fornecedores import PaginaFornecedores
from baliza.interface.icones import icone
from baliza.interface.tema import CORES

AREAS = [
    ("inicio", "Início"),
    ("consulta", "Consulta"),
    ("fornecedores", "Fornecedores"),
    ("entidade", "Entidade"),
    ("configuracoes", "Configurações"),
]
LARGURA_NAVEGACAO = 232


class PaginaEmConstrucao(QWidget):
    def __init__(self, titulo: str, descricao: str) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 32, 40, 32)
        layout.setSpacing(16)
        layout.addWidget(texto(titulo, "titulo"))
        layout.addWidget(texto(descricao, "apoio"))
        layout.addStretch()


DESCRICOES = {
    "inicio": "O resumo do que está cadastrado chega na versão 0.7.",
    "consulta": "Busque o fornecedor e confira onde cada conta está cadastrada.",
    "fornecedores": "Fornecedores, com as contas bancárias e as chaves Pix.",
    "entidade": "Os dados e as contas da entidade.",
    "configuracoes": "Bancos e, nas próximas versões, impressão, backup e senha.",
}


class Navegacao(QFrame):
    """Barra lateral. Setas para cima e para baixo trocam de área quando ela tem o foco."""

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("navegacao")
        self.setFixedWidth(LARGURA_NAVEGACAO)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 20, 12, 20)
        layout.setSpacing(4)

        cabecalho = QHBoxLayout()
        cabecalho.setContentsMargins(8, 4, 0, 20)
        cabecalho.setSpacing(12)
        self.logo = QLabel()
        self.logo.setFixedSize(32, 32)
        self.logo.setStyleSheet(f"background: {CORES['accent/subtle']}; border-radius: 6px;")
        nomes = QVBoxLayout()
        nomes.setSpacing(0)
        self.nome_entidade = texto("Baliza")
        self.nome_entidade.setStyleSheet("font-weight: 500;")
        nomes.addWidget(self.nome_entidade)
        nomes.addWidget(texto("Baliza", "ajuda"))
        cabecalho.addWidget(self.logo)
        cabecalho.addLayout(nomes, 1)
        layout.addLayout(cabecalho)

        self.grupo = QButtonGroup(self)
        self.grupo.setExclusive(True)
        self.botoes: dict[str, QPushButton] = {}
        for numero, (chave, rotulo) in enumerate(AREAS, start=1):
            b = QPushButton(rotulo)
            b.setProperty("papel", "nav")
            b.setCheckable(True)
            b.setIcon(icone(chave, CORES["text/secondary"]))
            b.setIconSize(QSize(16, 16))
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setToolTip(f"{rotulo} (Ctrl+{numero})")
            b.setAccessibleName(rotulo)
            b.installEventFilter(self)
            self.grupo.addButton(b)
            self.botoes[chave] = b
            layout.addWidget(b)
        layout.addStretch()

    def mostrar_entidade(self, entidade: Entidade | None) -> None:
        """RF16: logo e nome da entidade no topo da navegação. Sem logo, o espaço fica vazio."""
        if entidade is None:
            return
        nome = entidade.razao_social
        self.nome_entidade.setText(nome if len(nome) <= 24 else nome[:23] + "…")
        self.nome_entidade.setToolTip(nome)
        self.logo.setPixmap(pixmap_do_logo(entidade.logo, 32))

    def eventFilter(self, objeto, evento) -> bool:  # noqa: N802 (nome do Qt)
        if evento.type() == evento.Type.KeyPress and evento.key() in (
            Qt.Key.Key_Up,
            Qt.Key.Key_Down,
        ):
            botoes = list(self.botoes.values())
            atual = botoes.index(objeto)
            passo = 1 if evento.key() == Qt.Key.Key_Down else -1
            proximo = botoes[(atual + passo) % len(botoes)]
            proximo.setFocus()
            proximo.click()
            return True
        return super().eventFilter(objeto, evento)


class AreaPrincipal(QWidget):
    def __init__(self, base: BaseDeDados | None = None) -> None:
        super().__init__()
        self.base = base
        self.setObjectName("fundo")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.navegacao = Navegacao()
        self.paginas = QStackedWidget()
        layout.addWidget(self.navegacao)
        layout.addWidget(self.paginas, 1)
        self.indice: dict[str, QWidget] = {}
        for numero, (chave, rotulo) in enumerate(AREAS, start=1):
            pagina = self.criar_pagina(chave, rotulo)
            self.indice[chave] = pagina
            self.paginas.addWidget(pagina)
            self.navegacao.botoes[chave].clicked.connect(lambda _=False, c=chave: self.ir_para(c))
            atalho = QShortcut(QKeySequence(f"Ctrl+{numero}"), self)
            atalho.activated.connect(lambda c=chave: self.ir_para(c))
        if base is not None:
            self.navegacao.mostrar_entidade(obter_entidade(base.conexao))
        self.ir_para("inicio")

    def criar_pagina(self, chave: str, rotulo: str) -> QWidget:
        if chave == "entidade" and self.base is not None:
            pagina = PaginaEntidade(obter_entidade(self.base.conexao), PaginaContas(self.base))
            pagina.salva.connect(self._salvar_entidade)
            return pagina
        if chave == "consulta" and self.base is not None:
            return PaginaConsulta(self.base)
        if chave == "fornecedores" and self.base is not None:
            return PaginaFornecedores(self.base)
        if chave == "configuracoes" and self.base is not None:
            return PaginaConfiguracoes(self.base)
        return PaginaEmConstrucao(rotulo, DESCRICOES[chave])

    def _salvar_entidade(self, entidade: Entidade) -> None:
        salvar_entidade(self.base.conexao, entidade)
        self.base.salvar()
        self.navegacao.mostrar_entidade(entidade)

    def ir_para(self, chave: str) -> None:
        self.paginas.setCurrentWidget(self.indice[chave])
        self.navegacao.botoes[chave].setChecked(True)
        for nome, b in self.navegacao.botoes.items():
            cor = CORES["accent/default"] if nome == chave else CORES["text/secondary"]
            b.setIcon(icone(nome, cor))

    def area_atual(self) -> str:
        atual = self.paginas.currentWidget()
        return next(c for c, p in self.indice.items() if p is atual)
