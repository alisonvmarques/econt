"""Consulta: busca (T08) e resultado com onde cada conta está cadastrada (T09), e a
impressão dos dados para pagamento (I01). A impressão de dados bancários só existe aqui (RF06).
"""

from __future__ import annotations

from datetime import datetime
from html import escape

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from baliza.dados.banco import BaseDeDados
from baliza.dados.consulta import Encontrado, ResultadoConsulta, buscar, consultar
from baliza.dados.entidade import obter_entidade
from baliza.interface.componentes import (
    EstadoVazio,
    Tabela,
    aviso,
    botao,
    cartao,
    empilhar,
    etiqueta,
    linha_de_acoes,
    mudar_aviso,
    texto,
)
from baliza.interface.impressao import abrir_janela_impressao
from baliza.interface.impressoes import dados_para_pagamento
from baliza.interface.tema import CORES

FORMATO_IMPRESSAO = "formato_impressao"
FORMATOS = {
    "folha_completa": "Folha completa",
    "meia_folha": "Meia folha",
}


def formato_escolhido(base: BaseDeDados) -> str:
    """RF19: vale o que estiver nas Configurações; sem escolha, folha completa."""
    formato = base.configuracao(FORMATO_IMPRESSAO, "folha_completa")
    return formato if formato in FORMATOS else "folha_completa"


def escolher(pai: QWidget, titulo: str, mensagem: str, opcoes: list[str]) -> int | None:
    """Pergunta com várias respostas. Devolve a posição da escolhida, ou None se cancelou."""
    caixa = QMessageBox(pai)
    caixa.setWindowTitle(titulo)
    caixa.setText(mensagem)
    botoes = [caixa.addButton(o, QMessageBox.ButtonRole.AcceptRole) for o in opcoes]
    cancelar = caixa.addButton("Cancelar", QMessageBox.ButtonRole.RejectRole)
    caixa.setDefaultButton(botoes[0])
    caixa.exec()
    clicado = caixa.clickedButton()
    return None if clicado is cancelar else botoes.index(clicado)


def _destacar(texto_original: str, trecho: tuple[int, int] | None) -> str:
    if not trecho:
        return escape(texto_original)
    a, b = trecho
    cor = CORES["accent/default"]
    return (
        escape(texto_original[:a])
        + f'<b style="color: {cor};">{escape(texto_original[a:b])}</b>'
        + escape(texto_original[b:])
    )


class LinhaEncontrado(QWidget):
    """Um fornecedor na lista da busca, com o trecho que bateu destacado."""

    def __init__(self, e: Encontrado) -> None:
        super().__init__()
        f = e.fornecedor
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        coluna = QVBoxLayout()
        coluna.setSpacing(2)
        nome = _destacar(f.razao_social, e.trecho if e.campo == "razao_social" else None)
        if e.campo == "nome_fantasia":
            nome += (
                f' <span style="color: {CORES["text/secondary"]};">· '
                + _destacar(f.nome_fantasia, e.trecho)
                + "</span>"
            )
        documento = (
            _destacar_documento(f.documento_formatado, f.documento, e.trecho)
            if e.campo == "documento"
            else escape(f.documento_formatado)
        )
        for conteudo in (nome, documento):
            rotulo = QLabel(conteudo)
            rotulo.setTextFormat(Qt.TextFormat.RichText)
            coluna.addWidget(rotulo)
        layout.addLayout(coluna, 1)
        layout.addWidget(texto(e.resumo, "ajuda"))


def _destacar_documento(formatado: str, puro: str, trecho: tuple[int, int]) -> str:
    """O trecho bateu no documento sem pontuação; acha as posições no documento formatado."""
    posicoes = [i for i, c in enumerate(formatado) if c.isalnum()]
    a, b = trecho
    return _destacar(formatado, (posicoes[a], posicoes[b - 1] + 1))


class Resultado(QWidget):
    """T09 · O fornecedor, suas contas e chaves ativas e onde cada uma está cadastrada."""

    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        self.voltar = botao("← Resultados da busca", "link")
        layout.addLayout(linha_de_acoes(self.voltar, alinhar="esquerda"))
        quadro = cartao()
        interno = QVBoxLayout(quadro)
        interno.setContentsMargins(24, 20, 24, 20)
        interno.setSpacing(14)
        topo = QHBoxLayout()
        nomes = QVBoxLayout()
        nomes.setSpacing(2)
        self.nome = texto("", "secao")
        self.documento = texto("", "apoio")
        nomes.addWidget(self.nome)
        nomes.addWidget(self.documento)
        topo.addLayout(nomes, 1)
        self.imprimir = botao("Imprimir meia folha", "principal")
        topo.addWidget(self.imprimir, 0, Qt.AlignmentFlag.AlignTop)
        interno.addLayout(topo)
        self.alerta = aviso("", "erro")
        interno.addWidget(self.alerta)
        self.vazio = texto("", "apoio")
        interno.addWidget(self.vazio)
        self.tabela = Tabela(["Conta ou chave", "Dados"])
        self.tabela.setSelectionMode(Tabela.SelectionMode.NoSelection)
        self.tabela.celulas_inteiras()
        self.tabela.setWordWrap(False)
        interno.addWidget(self.tabela)
        layout.addWidget(quadro)
        self.fila = aviso("", "info")
        self.fila.setVisible(False)
        layout.addWidget(self.fila)
        self.conferido = texto("", "ajuda")
        layout.addWidget(self.conferido)
        layout.addStretch()

    def mostrar(self, r: ResultadoConsulta, quando: datetime) -> None:
        f = r.fornecedor
        self.nome.setText(f.razao_social)
        fantasia = f" · Nome fantasia: {f.nome_fantasia}" if f.nome_fantasia else ""
        self.documento.setText(f"{f.nome_do_documento} {f.documento_formatado}{fantasia}")
        sem = r.sem_cadastro
        if sem:
            nomes = [
                ("a conta " if s.item.tipo == "conta" else "a chave Pix ") + s.item.dados
                for s in sem
            ]
            if len(nomes) == 1:
                mensagem = (
                    f"{nomes[0][0].upper()}{nomes[0][1:]} não está cadastrada em nenhuma conta "
                    "da entidade. Não use para pagar até cadastrar o favorecido no banco."
                )
            else:
                mensagem = (
                    f"{len(nomes)} contas ou chaves não estão cadastradas em nenhuma conta da "
                    f"entidade: {'; '.join(nomes)}. Não use essas para pagar até cadastrar o "
                    "favorecido no banco."
                )
            mudar_aviso(self.alerta, mensagem, "erro")
        self.alerta.setVisible(bool(sem))
        vazio = ""
        if not r.cadastros:
            vazio = "Este fornecedor não tem contas nem chaves Pix ativas: não há dados para pagar."
        elif not r.contas_entidade:
            vazio = "Não há contas ativas da entidade. Cadastre em Entidade › Contas."
        self.vazio.setText(vazio)
        self.vazio.setVisible(bool(vazio))
        self.tabela.setVisible(bool(r.cadastros))
        self.imprimir.setEnabled(bool(r.cadastros))

        self.tabela.clear()
        colunas = ["Conta ou chave", "Dados", *[c.descricao for c in r.contas_entidade]]
        self.tabela.setColumnCount(len(colunas))
        self.tabela.setHorizontalHeaderLabels(colunas)
        cabecalho = self.tabela.horizontalHeader()
        cabecalho.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        cabecalho.setSectionResizeMode(len(colunas) - 1, QHeaderView.ResizeMode.Stretch)
        self.tabela.setRowCount(len(r.cadastros))
        for linha, cadastro in enumerate(r.cadastros):
            pecas = [
                empilhar(texto(cadastro.item.nome), margem=12),
                empilhar(texto(cadastro.item.dados), margem=12),
            ]
            for conta in r.contas_entidade:
                if r.cadastrada(cadastro, conta):
                    marca = etiqueta("✓ Cadastrada", "sucesso")
                else:
                    marca = etiqueta("✕ Não cadastrada", "perigo")
                pecas.append(empilhar(marca, margem=12))
            fundo = f"background: {CORES['status/danger-bg']};" if cadastro.sem_cadastro else ""
            for coluna, peca in enumerate(pecas):
                peca.setObjectName("celula")
                peca.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
                peca.setStyleSheet(f"#celula {{ {fundo} }}")
                self.tabela.celula(linha, coluna, "")
                self.tabela.setCellWidget(linha, coluna, peca)
        self.tabela.ajustar()
        altura = self.tabela.horizontalHeader().height() + sum(
            self.tabela.rowHeight(i) for i in range(self.tabela.rowCount())
        )
        self.tabela.setFixedHeight(altura + 4)
        self.conferido.setText(f"Conferido em {quando:%d/%m/%Y às %H:%M}")


class PaginaConsulta(QWidget):
    def __init__(self, base: BaseDeDados) -> None:
        super().__init__()
        self.base = base
        self.resultado_atual: ResultadoConsulta | None = None
        self.na_fila: ResultadoConsulta | None = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 32, 40, 32)
        layout.setSpacing(12)
        layout.addWidget(texto("Consulta", "titulo"))
        self.busca = QLineEdit()
        self.busca.setPlaceholderText("Buscar por razão social, nome fantasia ou CNPJ/CPF")
        self.busca.setAccessibleName("Buscar fornecedor")
        self.busca.setClearButtonEnabled(True)
        layout.addWidget(self.busca)
        self.areas = QStackedWidget()
        layout.addWidget(self.areas, 1)

        self.lista_area = QWidget()
        coluna = QVBoxLayout(self.lista_area)
        coluna.setContentsMargins(0, 4, 0, 0)
        coluna.setSpacing(8)
        self.quantos = texto("Digite parte do nome ou do CNPJ/CPF do fornecedor.", "ajuda")
        coluna.addWidget(self.quantos)
        self.nada = EstadoVazio(
            "Nenhum fornecedor encontrado",
            "Confira a grafia ou busque pelo CNPJ ou CPF. Fornecedores inativos não aparecem "
            "na Consulta.",
        )
        coluna.addWidget(self.nada, 0, Qt.AlignmentFlag.AlignHCenter)
        self.lista = QListWidget()
        self.lista.setObjectName("resultados")
        self.lista.setAccessibleName("Fornecedores encontrados")
        coluna.addWidget(self.lista, 1)
        self.dica = texto(
            "O trecho que bateu com a busca fica destacado. Clique no fornecedor, ou use Enter, "
            "para ver as contas.",
            "ajuda",
        )
        coluna.addWidget(self.dica)
        coluna.addStretch()
        self.areas.addWidget(self.lista_area)
        self.resultado = Resultado()
        self.areas.addWidget(self.resultado)

        self.busca.textChanged.connect(lambda _: self.atualizar_busca())
        self.busca.returnPressed.connect(self._abrir_primeiro)
        self.lista.itemClicked.connect(self._abrir_item)
        self.lista.itemActivated.connect(self._abrir_item)
        self.resultado.voltar.clicked.connect(self.voltar_para_busca)
        self.resultado.imprimir.clicked.connect(self.imprimir)
        self.busca.installEventFilter(self)
        self.atualizar_busca()

    def eventFilter(self, objeto, evento) -> bool:  # noqa: N802 (nome do Qt)
        if objeto is self.busca and evento.type() == evento.Type.KeyPress:
            if evento.key() == Qt.Key.Key_Down and self.lista.count():
                self.areas.setCurrentWidget(self.lista_area)
                self.lista.setFocus()
                self.lista.setCurrentRow(0)
                return True
            if evento.key() == Qt.Key.Key_Escape:
                self.busca.clear()
                return True
        return super().eventFilter(objeto, evento)

    def showEvent(self, evento) -> None:  # noqa: N802 (nome do Qt)
        if self.resultado_atual is not None:
            self.abrir(self.resultado_atual.fornecedor.id)
        else:
            self.atualizar_busca()
        self.busca.setFocus()
        super().showEvent(evento)

    def atualizar_busca(self) -> None:
        termo = self.busca.text()
        encontrados = buscar(self.base.conexao, termo)
        self.lista.clear()
        for e in encontrados:
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, e.fornecedor.id)
            item.setData(Qt.ItemDataRole.AccessibleTextRole, e.fornecedor.razao_social)
            linha = LinhaEncontrado(e)
            item.setSizeHint(linha.sizeHint())
            self.lista.addItem(item)
            self.lista.setItemWidget(item, linha)
        if not termo.strip():
            self.quantos.setText("Digite parte do nome ou do CNPJ/CPF do fornecedor.")
        elif not encontrados:
            self.quantos.setText("Nenhum fornecedor ativo encontrado.")
        else:
            n = len(encontrados)
            self.quantos.setText(
                "1 fornecedor encontrado" if n == 1 else f"{n} fornecedores encontrados"
            )
        self.lista.setVisible(bool(encontrados))
        self.nada.setVisible(bool(termo.strip()) and not encontrados)
        self.dica.setVisible(bool(encontrados))
        self.resultado_atual = None
        self.areas.setCurrentWidget(self.lista_area)

    def _abrir_item(self, item: QListWidgetItem) -> None:
        self.abrir(item.data(Qt.ItemDataRole.UserRole))

    def _abrir_primeiro(self) -> None:
        if self.lista.count():
            self._abrir_item(self.lista.item(0))

    def abrir(self, fornecedor_id: int) -> None:
        self.resultado_atual = consultar(self.base.conexao, fornecedor_id)
        self.resultado.mostrar(self.resultado_atual, datetime.now())
        self._mostrar_fila()
        self.areas.setCurrentWidget(self.resultado)
        self.resultado.imprimir.setFocus()

    def voltar_para_busca(self) -> None:
        self.resultado_atual = None
        self.areas.setCurrentWidget(self.lista_area)
        self.busca.setFocus()
        self.busca.selectAll()

    # Impressão -----------------------------------------------------------------------------

    def _mostrar_fila(self) -> None:
        if self.na_fila is None:
            self.resultado.fila.setVisible(False)
            return
        mudar_aviso(
            self.resultado.fila,
            f"A meia folha de {self.na_fila.fornecedor.razao_social} está guardada: sai na "
            "mesma folha do próximo fornecedor que você imprimir.",
            "info",
        )
        self.resultado.fila.setVisible(True)

    def imprimir(self) -> None:
        atual = self.resultado_atual
        if atual is None or not atual.cadastros:
            return
        entidade = obter_entidade(self.base.conexao)
        if formato_escolhido(self.base) == "meia_folha":
            abrir_janela_impressao(self, dados_para_pagamento([atual], entidade))
            return
        if self.na_fila is not None and self.na_fila.fornecedor.id != atual.fornecedor.id:
            # Folha completa com os dois: o guardado em cima, este embaixo.
            outro = consultar(self.base.conexao, self.na_fila.fornecedor.id)
            if abrir_janela_impressao(self, dados_para_pagamento([outro, atual], entidade)):
                self.na_fila = None
            self._mostrar_fila()
            return
        escolha = escolher(
            self,
            "Imprimir meia folha",
            "A folha completa tem espaço para dois fornecedores. Imprimir este agora, com a "
            "metade de baixo em branco, ou guardar para sair junto com o próximo?",
            ["Imprimir agora", "Guardar para o próximo"],
        )
        if escolha == 0:
            abrir_janela_impressao(self, dados_para_pagamento([atual], entidade))
        elif escolha == 1:
            self.na_fila = atual
            self._mostrar_fila()
