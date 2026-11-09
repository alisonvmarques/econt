"""Ficha do fornecedor · aba Cadastros (T16): em quais contas da entidade cada conta e chave
Pix está cadastrada como favorecido (RF11, RF12, RF13, RN12)."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QCheckBox, QHeaderView, QVBoxLayout, QWidget

from baliza.dados.banco import BaseDeDados
from baliza.dados.contas import listar_contas
from baliza.dados.fornecedores import Fornecedor
from baliza.dados.marcacoes import (
    Item,
    definir_marcacao,
    itens_do_fornecedor,
    marcacoes_do_item,
    marcar_todas,
)
from baliza.interface.componentes import (
    Tabela,
    aviso,
    botao,
    centralizar,
    empilhar,
    etiqueta,
    perguntar,
    texto,
)
from baliza.interface.tema import CORES


class PainelCadastros(QWidget):
    alterado = Signal()

    def __init__(self, base: BaseDeDados) -> None:
        super().__init__()
        self.base = base
        self.fornecedor: Fornecedor | None = None
        self.caixas: dict[tuple[int, int], QCheckBox] = {}
        self.botoes_todas: list = []
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 16, 0, 0)
        layout.setSpacing(12)
        layout.addWidget(
            texto(
                "Marque em quais contas da entidade cada conta e chave Pix está cadastrada como "
                "favorecido no banco. As marcações são salvas na hora.",
                "apoio",
            )
        )
        self.situacao = aviso("", "info")
        self.situacao.setVisible(False)
        layout.addWidget(self.situacao)
        self.vazia = texto("", "apoio")
        layout.addWidget(self.vazia)
        self.tabela = Tabela(["Conta ou chave"])
        self.tabela.setSelectionMode(Tabela.SelectionMode.NoSelection)
        self.tabela.celulas_inteiras()
        self.tabela.setWordWrap(False)
        layout.addWidget(self.tabela)
        self.rodape = texto("", "ajuda")
        layout.addWidget(self.rodape)
        layout.addStretch()

    def showEvent(self, evento) -> None:  # noqa: N802 (nome do Qt)
        # As contas da entidade podem ter mudado na área Entidade.
        if self.fornecedor is not None:
            self.mostrar(self.fornecedor)
        super().showEvent(evento)

    def mostrar(self, fornecedor: Fornecedor) -> None:
        self.fornecedor = fornecedor
        conexao = self.base.conexao
        todas_contas = listar_contas(conexao)
        # Mesma ordem de colunas da Consulta e da impressão: a ordem de cadastro.
        contas = sorted((c for c in todas_contas if c.ativa), key=lambda c: c.id)
        todos_itens = itens_do_fornecedor(conexao, fornecedor.id)
        itens = [i for i in todos_itens if i.ativo]
        self.itens = itens
        self.contas = contas

        self.situacao.setVisible(not fornecedor.ativo)
        self.situacao.setText(
            "ⓘ  Fornecedor inativo: as marcações estão guardadas e voltam como estavam quando "
            "ele for reativado."
        )
        vazio = ""
        if not contas:
            vazio = "Cadastre as contas da entidade em Entidade › Contas para marcar aqui."
        elif not itens:
            vazio = "Cadastre contas bancárias ou chaves Pix na aba Contas e Pix para marcar aqui."
        self.vazia.setText(vazio)
        self.vazia.setVisible(bool(vazio))
        self.tabela.setVisible(not vazio)
        ocultos = []
        if len(todos_itens) > len(itens):
            ocultos.append("contas e chaves inativas do fornecedor")
        if len(todas_contas) > len(contas):
            ocultos.append("contas inativas da entidade")
        self.rodape.setText(
            f"Não aparecem aqui: {' e '.join(ocultos)}. As marcações delas ficam guardadas."
            if ocultos
            else ""
        )
        self.rodape.setVisible(bool(ocultos) and not vazio)
        if vazio:
            return

        self.tabela.clear()
        self.caixas.clear()
        self.botoes_todas = []
        self.tabela.setColumnCount(len(contas) + 2)
        self.tabela.setHorizontalHeaderLabels(
            ["Conta ou chave", *[c.descricao for c in contas], ""]
        )
        cabecalho = self.tabela.horizontalHeader()
        cabecalho.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        cabecalho.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.tabela.setRowCount(len(itens))
        editavel = fornecedor.ativo
        for linha, item in enumerate(itens):
            marcadas = marcacoes_do_item(conexao, item)
            for coluna, conta in enumerate(contas, start=1):
                caixa = QCheckBox()
                caixa.setChecked(conta.id in marcadas)
                caixa.setEnabled(editavel)
                caixa.setAccessibleName(f"{item.rotulo} cadastrada em {conta.descricao}")
                caixa.setToolTip(f"{item.rotulo} · {conta.descricao}")
                caixa.toggled.connect(lambda marcar, i=item, c=conta.id: self._marcar(i, c, marcar))
                self.caixas[(item.id if item.tipo == "conta" else -item.id, conta.id)] = caixa
                self.tabela.celula(linha, coluna, "")
                self.tabela.setCellWidget(linha, coluna, centralizar(caixa))
            todas = botao("Marcar todas")
            todas.setEnabled(editavel)
            todas.setAccessibleName(f"Marcar todas para {item.rotulo}")
            todas.clicked.connect(lambda _=False, i=item: self._marcar_todas(i))
            self.botoes_todas.append(todas)
            self.tabela.celula(linha, len(contas) + 1, "")
            self.tabela.setCellWidget(linha, len(contas) + 1, centralizar(todas))
            self._mostrar_linha(linha, item)
        self.tabela.ajustar()
        altura = self.tabela.horizontalHeader().height() + sum(
            self.tabela.rowHeight(i) for i in range(self.tabela.rowCount())
        )
        self.tabela.setFixedHeight(altura + 4)

    def caixa(self, item: Item, conta_entidade_id: int) -> QCheckBox:
        return self.caixas[(item.id if item.tipo == "conta" else -item.id, conta_entidade_id)]

    def _mostrar_linha(self, linha: int, item: Item) -> None:
        """Sem cadastro em nenhuma conta: destaque na linha e o aviso por escrito (RN08)."""
        sem_cadastro = not any(
            c.id in marcacoes_do_item(self.base.conexao, item) for c in self.contas
        )
        pecas = [texto(item.rotulo)]
        if sem_cadastro:
            pecas.append(etiqueta("⚠ Não cadastrada em nenhuma conta", "perigo"))
        self.tabela.celula(linha, 0, "")
        self.tabela.setCellWidget(linha, 0, empilhar(*pecas, margem=12))
        fundo = f"background: {CORES['status/danger-bg']};" if sem_cadastro else ""
        for coluna in range(self.tabela.columnCount()):
            peca = self.tabela.cellWidget(linha, coluna)
            if peca is not None:
                peca.setObjectName("celula")
                peca.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
                peca.setStyleSheet(f"#celula {{ {fundo} }}")

    def _marcar(self, item: Item, conta_entidade_id: int, marcar: bool) -> None:
        definir_marcacao(self.base.conexao, item, conta_entidade_id, marcar)
        self.base.salvar()
        self._mostrar_linha(self.itens.index(item), item)
        self.tabela.ajustar()
        self.alterado.emit()

    def _marcar_todas(self, item: Item) -> None:
        if not perguntar(
            self,
            "Marcar todas as contas?",
            f"{item.rotulo} fica marcada como cadastrada nas {len(self.contas)} contas ativas "
            "da entidade.",
            "Marcar todas",
        ):
            return
        marcar_todas(self.base.conexao, item)
        self.base.salvar()
        self.mostrar(self.fornecedor)
        self.alterado.emit()
