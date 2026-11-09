"""Área Configurações: impressão (T22), backup (T23) e bancos (T24)."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QButtonGroup, QRadioButton, QVBoxLayout, QWidget

from baliza.dados.banco import BaseDeDados
from baliza.interface.backup import PaginaBackup
from baliza.interface.bancos import PaginaBancos
from baliza.interface.componentes import Abas, cartao, confirmar_rapido, texto
from baliza.interface.consulta import FORMATO_IMPRESSAO, FORMATOS, formato_escolhido

EXPLICACOES = {
    "folha_completa": "Folha A4 com dois fornecedores e a linha de corte no meio.",
    "meia_folha": "A metade de uma A4 já cortada, colocada na impressora. Um fornecedor por vez.",
}


class PaginaImpressao(QWidget):
    """RF19 · Formato da impressão dos dados para pagamento, salvo na hora."""

    def __init__(self, base: BaseDeDados) -> None:
        super().__init__()
        self.base = base
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 20, 0, 0)
        layout.setSpacing(12)
        quadro = cartao()
        quadro.setMaximumWidth(720)
        interno = QVBoxLayout(quadro)
        interno.setContentsMargins(24, 20, 24, 20)
        interno.setSpacing(10)
        interno.addWidget(texto("Formato dos dados para pagamento", "secao"))
        interno.addWidget(texto("Vale para as próximas impressões feitas na Consulta.", "apoio"))
        self.grupo = QButtonGroup(self)
        self.opcoes: dict[str, QRadioButton] = {}
        for chave, rotulo in FORMATOS.items():
            opcao = QRadioButton(rotulo)
            self.grupo.addButton(opcao)
            self.opcoes[chave] = opcao
            interno.addWidget(opcao)
            explicacao = texto(EXPLICACOES[chave], "ajuda")
            explicacao.setContentsMargins(28, 0, 0, 6)
            interno.addWidget(explicacao)
        layout.addWidget(quadro)
        layout.addStretch()
        self.opcoes[formato_escolhido(base)].setChecked(True)
        for chave, opcao in self.opcoes.items():
            opcao.toggled.connect(lambda marcada, c=chave: marcada and self._escolher(c))

    def _escolher(self, formato: str) -> None:
        self.base.definir_configuracao(FORMATO_IMPRESSAO, formato)
        self.base.salvar()
        confirmar_rapido(self, f"Formato salvo: {FORMATOS[formato]}.")


class PaginaConfiguracoes(QWidget):
    restaurado = Signal(object)

    def __init__(self, base: BaseDeDados) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 32, 40, 32)
        layout.setSpacing(16)
        layout.addWidget(texto("Configurações", "titulo"))
        self.abas = Abas()
        self.impressao = PaginaImpressao(base)
        self.bancos = PaginaBancos(base)
        self.backup = PaginaBackup(base)
        self.backup.restaurado.connect(self.restaurado.emit)
        self.abas.addTab(self.impressao, "Impressão")
        self.abas.addTab(self.backup, "Backup")
        self.abas.addTab(self.bancos, "Bancos")
        layout.addWidget(self.abas, 1)
