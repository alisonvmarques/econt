"""Configurações · Bancos (T24): lista oficial e cadastro manual de banco (RF26, RN13)."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QHeaderView, QLineEdit, QVBoxLayout, QWidget

from baliza.dados.banco import BaseDeDados
from baliza.dados.lista_bancos import cadastrar_banco_manual, listar_bancos, problemas_do_banco
from baliza.interface.componentes import (
    Campo,
    Dialogo,
    Tabela,
    botao,
    confirmar_rapido,
    empilhar,
    etiqueta,
    texto,
)


class DialogoBanco(Dialogo):
    """Código e nome de um banco que ainda não está na lista oficial."""

    def __init__(self, pai: QWidget | None, base: BaseDeDados) -> None:
        super().__init__(pai, "Cadastrar banco", "Cadastrar banco")
        self.base = base
        self.codigo = Campo("Código", "O código de compensação, com até 3 números.")
        self.nome = Campo("Nome do banco")
        self.corpo.addWidget(self.codigo)
        self.corpo.addWidget(self.nome)
        self.corpo.addWidget(
            texto("Use só para um banco que ainda não está na lista oficial.", "ajuda")
        )
        self.fechar_corpo()
        self.banco = None

    def ao_confirmar(self) -> None:
        erros = problemas_do_banco(self.base.conexao, self.codigo.valor(), self.nome.valor())
        for chave, campo in (("codigo", self.codigo), ("nome", self.nome)):
            if chave in erros:
                campo.mostrar_erro(erros[chave])
            else:
                campo.limpar_erro()
        if erros:
            (self.codigo if "codigo" in erros else self.nome).caixa.setFocus()
            return
        self.banco = cadastrar_banco_manual(
            self.base.conexao, self.codigo.valor(), self.nome.valor()
        )
        self.base.salvar()
        self.accept()


class PaginaBancos(QWidget):
    alterada = Signal()

    def __init__(self, base: BaseDeDados) -> None:
        super().__init__()
        self.base = base
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 20, 0, 0)
        layout.setSpacing(16)
        topo = QHBoxLayout()
        topo.setSpacing(12)
        self.busca = QLineEdit()
        self.busca.setPlaceholderText("Buscar banco por código ou nome")
        self.busca.setAccessibleName("Buscar banco")
        self.busca.setClearButtonEnabled(True)
        self.cadastrar = botao("Cadastrar banco", "principal")
        topo.addWidget(self.busca, 1)
        topo.addWidget(self.cadastrar)
        layout.addLayout(topo)
        self.tabela = Tabela(["Código", "Nome", "Origem"])
        self.tabela.setWordWrap(False)
        cabecalho = self.tabela.horizontalHeader()
        cabecalho.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        cabecalho.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        cabecalho.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        layout.addWidget(self.tabela, 1)
        self.rodape = texto("", "ajuda")
        layout.addWidget(self.rodape)
        self.busca.textChanged.connect(lambda _: self.atualizar())
        self.cadastrar.clicked.connect(self.abrir_cadastro)
        self.atualizar()

    def atualizar(self) -> None:
        bancos = listar_bancos(self.base.conexao, self.busca.text())
        self.tabela.setRowCount(len(bancos))
        for linha, banco in enumerate(bancos):
            self.tabela.celula(linha, 0, banco.codigo, banco.codigo)
            self.tabela.celula(linha, 1, banco.nome)
            if banco.origem == "manual":
                self.tabela.celula(linha, 2, "")
                self.tabela.setCellWidget(linha, 2, empilhar(etiqueta("✓ Cadastro manual")))
            else:
                self.tabela.celula(linha, 2, "Lista oficial")
        self.tabela.ajustar()
        quantos = "Nenhum banco encontrado." if not bancos else f"{len(bancos)} bancos."
        self.rodape.setText(
            f"{quantos} A lista oficial vem do Banco Central junto com cada versão do Baliza."
        )

    def abrir_cadastro(self) -> None:
        dialogo = self.criar_dialogo()
        if dialogo.exec():
            self.busca.setText(dialogo.banco.codigo)
            self.alterada.emit()
            confirmar_rapido(self, "Banco cadastrado.")

    def criar_dialogo(self) -> DialogoBanco:
        return DialogoBanco(self, self.base)
