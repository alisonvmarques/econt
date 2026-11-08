"""Área Configurações. As abas de impressão, backup e senha chegam nas próximas versões."""

from __future__ import annotations

from PySide6.QtWidgets import QVBoxLayout, QWidget

from baliza.dados.banco import BaseDeDados
from baliza.interface.bancos import PaginaBancos
from baliza.interface.componentes import Abas, texto


class PaginaConfiguracoes(QWidget):
    def __init__(self, base: BaseDeDados) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 32, 40, 32)
        layout.setSpacing(16)
        layout.addWidget(texto("Configurações", "titulo"))
        self.abas = Abas()
        self.bancos = PaginaBancos(base)
        self.abas.addTab(self.bancos, "Bancos")
        layout.addWidget(self.abas, 1)
