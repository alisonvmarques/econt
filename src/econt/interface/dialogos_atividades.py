"""Atividades: diálogos da atividade (T29), das arquivadas (T30), da coluna (T31) e das
etiquetas (T32)."""

from __future__ import annotations

from datetime import date

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QHeaderView,
    QListWidget,
    QListWidgetItem,
    QPlainTextEdit,
    QWidget,
)

from econt.dados.atividades import (
    Atividade,
    Coluna,
    ColunaInvalida,
    DadosAtividade,
    Etiqueta,
    atividades_com_etiqueta,
    coluna_de_conclusao,
    criar_atividade,
    criar_coluna,
    criar_etiqueta,
    definir_conclusao,
    editar_atividade,
    editar_etiqueta,
    excluir_atividade,
    excluir_etiqueta,
    listar_arquivadas,
    listar_etiquetas,
    problema_da_coluna,
    problema_da_etiqueta,
    problemas_da_atividade,
    renomear_coluna,
    restaurar_atividade,
)
from econt.dados.banco import BaseDeDados
from econt.dados.fornecedores import listar_fornecedores
from econt.dominio.atividades import (
    CORES_DE_ETIQUETA,
    PRIORIDADES,
    TAMANHO_DO_NOME_DA_COLUNA,
    TAMANHO_DO_NOME_DA_ETIQUETA,
    TAMANHO_DO_TITULO,
    AtividadeInvalida,
    formatar_prazo,
    ler_prazo,
)
from econt.dominio.formatos import data_ao_digitar
from econt.interface.componentes import (
    Campo,
    CampoBase,
    CampoEscolha,
    Dialogo,
    Tabela,
    botao,
    confirmar_rapido,
    formatar_ao_digitar,
    linha_de_acoes,
    perguntar,
    texto,
)
from econt.interface.tema import CORES, CORES_DAS_ETIQUETAS


def _data_hora(momento) -> str:
    return momento.strftime("%d/%m/%Y às %H:%M") if momento else ""


def bolinha(cor: str, tamanho: int = 12) -> QIcon:
    """A cor da etiqueta, para as listas. Vem do tema, como as etiquetas do cartão."""
    imagem = QPixmap(tamanho, tamanho)
    imagem.fill(Qt.GlobalColor.transparent)
    pintor = QPainter(imagem)
    pintor.setRenderHint(QPainter.RenderHint.Antialiasing)
    pintor.setPen(Qt.PenStyle.NoPen)
    pintor.setBrush(QColor(CORES[CORES_DAS_ETIQUETAS.get(cor, "text/secondary")]))
    pintor.drawEllipse(QRectF(1, 1, tamanho - 2, tamanho - 2))
    pintor.end()
    return QIcon(imagem)


class ListaDeEtiquetas(QListWidget):
    """Etiquetas para marcar. Tab chega à lista, as setas andam e Espaço marca (RNF05)."""

    def __init__(self) -> None:
        super().__init__()
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def mostrar(self, etiquetas: list[Etiqueta], marcadas: set[int]) -> None:
        self.clear()
        for e in etiquetas:
            item = QListWidgetItem(bolinha(e.cor), e.nome)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            marcada = e.id in marcadas
            item.setCheckState(Qt.CheckState.Checked if marcada else Qt.CheckState.Unchecked)
            item.setData(Qt.ItemDataRole.UserRole, e.id)
            item.setToolTip(f"Cor: {e.nome_da_cor}")
            self.addItem(item)
        if etiquetas:
            self.setCurrentRow(0)
        # Até 5 etiquetas à mostra sem rolar; com mais, a lista rola.
        self.ensurePolished()
        linha = self.sizeHintForRow(0) if etiquetas else 28
        self.setFixedHeight(min(max(len(etiquetas), 1), 5) * linha + 14)

    def marcadas(self) -> list[int]:
        return [
            self.item(i).data(Qt.ItemDataRole.UserRole)
            for i in range(self.count())
            if self.item(i).checkState() == Qt.CheckState.Checked
        ]

    def marcar(self, etiqueta_id: int, marcada: bool = True) -> None:
        for i in range(self.count()):
            if self.item(i).data(Qt.ItemDataRole.UserRole) == etiqueta_id:
                estado = Qt.CheckState.Checked if marcada else Qt.CheckState.Unchecked
                self.item(i).setCheckState(estado)

    def keyPressEvent(self, evento) -> None:  # noqa: N802 (nome do Qt)
        item = self.currentItem()
        if evento.key() == Qt.Key.Key_Space and item is not None:
            marcada = item.checkState() == Qt.CheckState.Checked
            item.setCheckState(Qt.CheckState.Unchecked if marcada else Qt.CheckState.Checked)
            return
        super().keyPressEvent(evento)


class CaixaDescricao(QPlainTextEdit):
    """Texto de várias linhas. Tab passa para o próximo campo e Ctrl+Enter salva (RNF05)."""

    def __init__(self, dialogo: Dialogo) -> None:
        super().__init__()
        self.dialogo = dialogo
        self.setTabChangesFocus(True)
        self.setFixedHeight(110)

    def keyPressEvent(self, evento) -> None:  # noqa: N802 (nome do Qt)
        if evento.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and (
            evento.modifiers() & Qt.KeyboardModifier.ControlModifier
        ):
            self.dialogo.ao_confirmar()
            return
        super().keyPressEvent(evento)


class DialogoAtividade(Dialogo):
    """T29 · Nova atividade ou edição, com todos os campos."""

    def __init__(
        self,
        pai: QWidget | None,
        base: BaseDeDados,
        coluna: Coluna,
        atividade: Atividade | None,
    ) -> None:
        titulo = "Editar atividade" if atividade else f"Nova atividade em {coluna.nome}"
        super().__init__(pai, titulo, "Salvar atividade")
        self.base = base
        self.coluna = coluna
        self.atividade = atividade
        self.atividade_id = atividade.id if atividade else None
        self.pediu_arquivar = False
        self.setMinimumWidth(600)

        self.titulo = Campo("Título", f"Até {TAMANHO_DO_TITULO} caracteres.")
        self.titulo.caixa.setMaxLength(TAMANHO_DO_TITULO)
        self.descricao = CampoBase(
            "Descrição", CaixaDescricao(self), "Opcional. Ctrl+Enter salva a atividade."
        )
        self.descricao.caixa.textChanged.connect(self.descricao.limpar_erro)
        self.prazo = Campo("Prazo", "Opcional. Só a data, assim: 25/11/2026.")
        self.prazo.caixa.setPlaceholderText("dd/mm/aaaa")
        self.prazo.caixa.setMaxLength(10)
        formatar_ao_digitar(self.prazo.caixa, data_ao_digitar)
        opcoes = [
            (
                f.id,
                self._nome_do_fornecedor(f.razao_social, f.nome_fantasia),
                f"{f.documento} {f.documento_formatado}",
            )
            for f in listar_fornecedores(base.conexao)
        ]
        if atividade and atividade.fornecedor_id and not atividade.fornecedor_ativo:
            nome = self._nome_do_fornecedor(
                atividade.fornecedor_razao_social, atividade.fornecedor_nome
            )
            opcoes.append((atividade.fornecedor_id, f"{nome} (inativo)"))
        self.fornecedor = CampoEscolha(
            "Fornecedor",
            opcoes,
            "Opcional. Digite parte do nome ou do CNPJ e escolha na lista.",
            busca=True,
        )
        self.fornecedor.caixa.lineEdit().setPlaceholderText("Sem fornecedor")
        self.prioridade = CampoEscolha("Prioridade", list(PRIORIDADES.items()), "Opcional.")
        self.lista_etiquetas = ListaDeEtiquetas()
        self.etiquetas = CampoBase(
            "Etiquetas", self.lista_etiquetas, "Opcional. Espaço marca e desmarca."
        )
        self.nova_etiqueta = botao("+ Nova etiqueta", "link")
        self.nova_etiqueta.clicked.connect(self._nova_etiqueta)
        for campo in (self.titulo, self.descricao):
            self.corpo.addWidget(campo)
        linha = QHBoxLayout()
        linha.setSpacing(12)
        linha.addWidget(self.prazo, 1, Qt.AlignmentFlag.AlignTop)
        linha.addWidget(self.prioridade, 1, Qt.AlignmentFlag.AlignTop)
        self.corpo.addLayout(linha)
        self.corpo.addWidget(self.fornecedor)
        self.corpo.addWidget(self.etiquetas)
        self.corpo.addLayout(linha_de_acoes(self.nova_etiqueta, alinhar="esquerda"))
        self._mostrar_etiquetas(set(atividade.etiquetas) if atividade else set())

        if atividade:
            self.titulo.definir(atividade.titulo)
            self.descricao.caixa.setPlainText(atividade.descricao)
            self.prazo.definir(formatar_prazo(atividade.prazo))
            self._definir_fornecedor(atividade.fornecedor_id)
            self.prioridade.definir(atividade.prioridade)
            datas = [f"Na coluna {atividade.coluna_nome}."]
            datas.append(f"Criada em {_data_hora(atividade.criado_em)}.")
            if atividade.alterado_em != atividade.criado_em:
                datas.append(f"Alterada em {_data_hora(atividade.alterado_em)}.")
            if atividade.movido_em != atividade.criado_em:
                datas.append(f"Mudou de coluna em {_data_hora(atividade.movido_em)}.")
            self.datas = texto(" ".join(datas), "ajuda")
            self.corpo.addWidget(self.datas)
        else:
            self._definir_fornecedor(None)
            self.prioridade.definir(0)

        self.arquivar = botao("Arquivar", "perigo") if atividade else None
        acoes = QHBoxLayout()
        acoes.setSpacing(12)
        if self.arquivar:
            self.arquivar.setToolTip("Tira a atividade do quadro sem apagar.")
            self.arquivar.clicked.connect(self._arquivar)
            acoes.addWidget(self.arquivar)
        acoes.addStretch()
        acoes.addWidget(self.cancelar)
        acoes.addWidget(self.confirmar)
        self.corpo.addLayout(acoes)
        self.titulo.caixa.setFocus()

    def _mostrar_etiquetas(self, marcadas: set[int]) -> None:
        etiquetas = listar_etiquetas(self.base.conexao)
        self.lista_etiquetas.mostrar(etiquetas, marcadas)
        self.lista_etiquetas.setVisible(bool(etiquetas))
        self.etiquetas.definir_ajuda(
            "Opcional. Espaço marca e desmarca."
            if etiquetas
            else "Nenhuma etiqueta ainda. Crie a primeira em Nova etiqueta."
        )

    def criar_dialogo_etiqueta(self) -> DialogoEtiqueta:
        return DialogoEtiqueta(self, self.base, None)

    def _nova_etiqueta(self) -> None:
        dialogo = self.criar_dialogo_etiqueta()
        if dialogo.exec():
            marcadas = {*self.lista_etiquetas.marcadas(), dialogo.etiqueta_id}
            self._mostrar_etiquetas(marcadas)
            self.lista_etiquetas.setFocus()

    def _definir_fornecedor(self, fornecedor_id: int | None) -> None:
        """Sem fornecedor, o campo fica vazio: é só começar a digitar para buscar."""
        if fornecedor_id:
            self.fornecedor.definir(fornecedor_id)
            self.fornecedor.caixa.lineEdit().setCursorPosition(0)  # o começo do nome à mostra
        else:
            self.fornecedor.caixa.setCurrentIndex(-1)
            self.fornecedor.caixa.setEditText("")

    @staticmethod
    def _nome_do_fornecedor(razao_social: str, fantasia: str) -> str:
        if fantasia and fantasia != razao_social:
            return f"{razao_social} ({fantasia})"
        return razao_social

    def _arquivar(self) -> None:
        self.pediu_arquivar = True
        self.accept()

    def _fornecedor_escolhido(self) -> int | None | str:
        """Id do fornecedor, None para sem fornecedor, ou "" se o texto não é da lista."""
        if not self.fornecedor.caixa.currentText().strip():
            return None
        return self.fornecedor.valor()

    def ao_confirmar(self) -> None:
        erros: dict[str, str] = {}
        prazo: date | None = None
        try:
            prazo = ler_prazo(self.prazo.valor())
        except AtividadeInvalida as erro:
            erros["prazo"] = str(erro)
        fornecedor = self._fornecedor_escolhido()
        if fornecedor == "":
            erros["fornecedor"] = "Escolha um fornecedor da lista ou apague o texto."
            fornecedor = None
        dados = DadosAtividade(
            self.titulo.valor(),
            self.descricao.caixa.toPlainText(),
            prazo,
            fornecedor,
            self.prioridade.valor() or 0,
            self.lista_etiquetas.marcadas(),
        )
        erros = problemas_da_atividade(self.base.conexao, dados) | erros
        campos = {
            "titulo": self.titulo,
            "prazo": self.prazo,
            "prioridade": self.prioridade,
            "fornecedor": self.fornecedor,
            "etiquetas": self.etiquetas,
        }
        for chave, campo in campos.items():
            if chave in erros:
                campo.mostrar_erro(erros[chave])
            else:
                campo.limpar_erro()
        if erros:
            next(campos[c] for c in campos if c in erros).caixa.setFocus()
            return
        if self.atividade_id is None:
            self.atividade_id = criar_atividade(self.base.conexao, self.coluna.id, dados)
        else:
            editar_atividade(self.base.conexao, self.atividade_id, dados)
        self.base.salvar()
        self.accept()


class DialogoColuna(Dialogo):
    """T31 · Nova coluna ou edição: nome e se é a coluna de conclusão (RN14, RN15)."""

    def __init__(self, pai: QWidget | None, base: BaseDeDados, coluna: Coluna | None) -> None:
        super().__init__(pai, "Editar coluna" if coluna else "Nova coluna", "Salvar coluna")
        self.base = base
        self.coluna_id = coluna.id if coluna else None
        self.nome = Campo("Nome da coluna", "Por exemplo: Aguardando banco.")
        self.nome.caixa.setMaxLength(TAMANHO_DO_NOME_DA_COLUNA)
        self.conclusao = QCheckBox("Coluna de conclusão")
        self.conclusao.setAccessibleName("Coluna de conclusão")
        atual = coluna_de_conclusao(base.conexao)
        ajuda = "Atividade nesta coluna conta como concluída e nunca aparece como atrasada."
        if atual and atual.id != self.coluna_id:
            ajuda += f" Só uma coluna pode ser de conclusão: marcar esta desmarca {atual.nome}."
        self.corpo.addWidget(self.nome)
        self.corpo.addWidget(self.conclusao)
        self.corpo.addWidget(texto(ajuda, "ajuda"))
        if coluna:
            self.nome.definir(coluna.nome)
            self.conclusao.setChecked(coluna.conclusao)
        self.fechar_corpo()
        self.nome.caixa.setFocus()

    def ao_confirmar(self) -> None:
        nome = self.nome.valor()
        erro = problema_da_coluna(self.base.conexao, nome, self.coluna_id)
        if erro:
            self.nome.mostrar_erro(erro)
            self.nome.caixa.setFocus()
            return
        conexao = self.base.conexao
        if self.coluna_id is None:
            self.coluna_id = criar_coluna(conexao, nome, self.conclusao.isChecked())
        else:
            renomear_coluna(conexao, self.coluna_id, nome)
            definir_conclusao(conexao, self.coluna_id, self.conclusao.isChecked())
        self.base.salvar()
        self.accept()


class DialogoArquivadas(Dialogo):
    """T30 · Atividades arquivadas, com Restaurar e Excluir definitivamente (RN17)."""

    def __init__(self, pai: QWidget | None, base: BaseDeDados) -> None:
        super().__init__(pai, "Atividades arquivadas", "Fechar")
        self.base = base
        self.mudou = False
        self.setMinimumWidth(680)
        self.corpo.addWidget(
            texto(
                "Restaurar devolve a atividade para o fim da coluna de onde saiu. Excluir "
                "definitivamente apaga a atividade e o histórico dela.",
                "apoio",
            )
        )
        self.vazia = texto("Nenhuma atividade arquivada.", "apoio")
        self.corpo.addWidget(self.vazia)
        self.tabela = Tabela(["Atividade", "Coluna de origem", "Arquivada em"])
        self.tabela.setWordWrap(False)
        cabecalho = self.tabela.horizontalHeader()
        cabecalho.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        cabecalho.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.tabela.setMinimumHeight(260)
        self.corpo.addWidget(self.tabela)
        self.restaurar = botao("Restaurar")
        self.excluir = botao("Excluir definitivamente", "perigo")
        self.restaurar.clicked.connect(self.restaurar_escolhida)
        self.excluir.clicked.connect(self.excluir_escolhida)
        self.tabela.escolhida.connect(lambda _: self.restaurar.setFocus())
        self.corpo.addLayout(linha_de_acoes(self.restaurar, self.excluir, alinhar="esquerda"))
        self.cancelar.setVisible(False)
        self.fechar_corpo()
        self.mostrar()

    def mostrar(self) -> None:
        arquivadas = listar_arquivadas(self.base.conexao)
        self.vazia.setVisible(not arquivadas)
        self.tabela.setVisible(bool(arquivadas))
        for b in (self.restaurar, self.excluir):
            b.setEnabled(bool(arquivadas))
        self.tabela.setRowCount(len(arquivadas))
        for linha, atividade in enumerate(arquivadas):
            self.tabela.celula(linha, 0, atividade.titulo, atividade.id)
            self.tabela.celula(linha, 1, atividade.coluna_nome)
            self.tabela.celula(linha, 2, _data_hora(atividade.arquivado_em))
        if arquivadas:
            self.tabela.setCurrentCell(0, 0)
        self.tabela.ajustar()

    def escolhida(self) -> int | None:
        linha = self.tabela.currentRow()
        return self.tabela.dado_da_linha(linha) if linha >= 0 else None

    def restaurar_escolhida(self) -> None:
        """Restaurar não perde nada, então não pede confirmação."""
        atividade_id = self.escolhida()
        if atividade_id is None:
            return
        try:
            restaurar_atividade(self.base.conexao, atividade_id)
        except ColunaInvalida as erro:
            self.vazia.setText(str(erro))
            self.vazia.setVisible(True)
            return
        self.base.salvar()
        self.mudou = True
        self.mostrar()
        confirmar_rapido(self, "Atividade restaurada.")

    def excluir_escolhida(self) -> None:
        atividade_id = self.escolhida()
        if atividade_id is None:
            return
        titulo = self.tabela.item(self.tabela.currentRow(), 0).text()
        if not perguntar(
            self,
            "Excluir definitivamente",
            f"Excluir a atividade {titulo}? Ela e o histórico dela são apagados e não "
            "dá para desfazer.",
            "Excluir definitivamente",
        ):
            return
        excluir_atividade(self.base.conexao, atividade_id)
        self.base.salvar()
        self.mudou = True
        self.mostrar()
        confirmar_rapido(self, "Atividade excluída.")


class DialogoEtiqueta(Dialogo):
    """Nova etiqueta ou edição: nome e cor, com as cores do tema (RF32, RN19)."""

    def __init__(self, pai: QWidget | None, base: BaseDeDados, etiqueta: Etiqueta | None) -> None:
        super().__init__(pai, "Editar etiqueta" if etiqueta else "Nova etiqueta", "Salvar etiqueta")
        self.base = base
        self.etiqueta_id = etiqueta.id if etiqueta else None
        self.setMinimumWidth(440)
        self.nome = Campo("Nome", f"Até {TAMANHO_DO_NOME_DA_ETIQUETA} caracteres. Ex.: Banco.")
        self.nome.caixa.setMaxLength(TAMANHO_DO_NOME_DA_ETIQUETA)
        self.cor = CampoEscolha("Cor", list(CORES_DE_ETIQUETA.items()))
        for indice, cor in enumerate(CORES_DE_ETIQUETA):
            self.cor.caixa.setItemIcon(indice, bolinha(cor))
        self.corpo.addWidget(self.nome)
        self.corpo.addWidget(self.cor)
        if etiqueta:
            self.nome.definir(etiqueta.nome)
            self.cor.definir(etiqueta.cor)
        self.nome.caixa.returnPressed.connect(self.ao_confirmar)
        self.fechar_corpo()
        self.nome.caixa.setFocus()

    def ao_confirmar(self) -> None:
        nome = self.nome.valor()
        erro = problema_da_etiqueta(self.base.conexao, nome, self.etiqueta_id)
        if erro:
            self.nome.mostrar_erro(erro)
            self.nome.caixa.setFocus()
            return
        cor = self.cor.valor() or "neutra"
        if self.etiqueta_id is None:
            self.etiqueta_id = criar_etiqueta(self.base.conexao, nome, cor)
        else:
            editar_etiqueta(self.base.conexao, self.etiqueta_id, nome, cor)
        self.base.salvar()
        self.accept()


class DialogoEtiquetas(Dialogo):
    """T32 · As etiquetas do quadro: criar, mudar nome e cor, e excluir."""

    def __init__(self, pai: QWidget | None, base: BaseDeDados) -> None:
        super().__init__(pai, "Etiquetas", "Fechar")
        self.base = base
        self.mudou = False
        self.setMinimumWidth(560)
        self.corpo.addWidget(
            texto(
                "Etiquetas marcam atividades parecidas, como Banco ou Prestação de contas. "
                "Busque pelo nome da etiqueta para ver só as atividades dela.",
                "apoio",
            )
        )
        self.vazia = texto("Nenhuma etiqueta ainda.", "apoio")
        self.corpo.addWidget(self.vazia)
        self.tabela = Tabela(["Etiqueta", "Cor", "Atividades"])
        self.tabela.setWordWrap(False)
        cabecalho = self.tabela.horizontalHeader()
        cabecalho.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        cabecalho.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.tabela.setMinimumHeight(220)
        self.corpo.addWidget(self.tabela)
        self.nova = botao("Nova etiqueta")
        self.editar = botao("Editar")
        self.excluir = botao("Excluir", "perigo")
        self.nova.clicked.connect(lambda: self.abrir(None))
        self.editar.clicked.connect(lambda: self.abrir(self.escolhida()))
        self.excluir.clicked.connect(self.excluir_escolhida)
        self.tabela.escolhida.connect(lambda _: self.abrir(self.escolhida()))
        self.corpo.addLayout(
            linha_de_acoes(self.nova, self.editar, self.excluir, alinhar="esquerda")
        )
        self.cancelar.setVisible(False)
        self.fechar_corpo()
        self.mostrar()

    def mostrar(self, escolher: int | None = None) -> None:
        etiquetas = listar_etiquetas(self.base.conexao)
        self.vazia.setVisible(not etiquetas)
        self.tabela.setVisible(bool(etiquetas))
        for b in (self.editar, self.excluir):
            b.setEnabled(bool(etiquetas))
        self.tabela.setRowCount(len(etiquetas))
        for linha, e in enumerate(etiquetas):
            self.tabela.celula(linha, 0, e.nome, e.id)
            self.tabela.item(linha, 0).setIcon(bolinha(e.cor))
            self.tabela.celula(linha, 1, e.nome_da_cor)
            self.tabela.celula(linha, 2, str(atividades_com_etiqueta(self.base.conexao, e.id)))
            if e.id == escolher:
                self.tabela.setCurrentCell(linha, 0)
        if etiquetas and self.tabela.currentRow() < 0:
            self.tabela.setCurrentCell(0, 0)
        self.tabela.ajustar()

    def escolhida(self) -> Etiqueta | None:
        linha = self.tabela.currentRow()
        if linha < 0 or not self.tabela.rowCount():
            return None
        etiqueta_id = self.tabela.dado_da_linha(linha)
        return next((e for e in listar_etiquetas(self.base.conexao) if e.id == etiqueta_id), None)

    def criar_dialogo_etiqueta(self, etiqueta: Etiqueta | None) -> DialogoEtiqueta:
        return DialogoEtiqueta(self, self.base, etiqueta)

    def abrir(self, etiqueta: Etiqueta | None) -> None:
        dialogo = self.criar_dialogo_etiqueta(etiqueta)
        if dialogo.exec():
            self.mudou = True
            self.mostrar(escolher=dialogo.etiqueta_id)
            confirmar_rapido(self, "Etiqueta salva.")

    def excluir_escolhida(self) -> None:
        etiqueta = self.escolhida()
        if etiqueta is None:
            return
        usadas = atividades_com_etiqueta(self.base.conexao, etiqueta.id)
        onde = (
            f" Ela sai de {usadas} {'atividade' if usadas == 1 else 'atividades'}; "
            "as atividades continuam."
            if usadas
            else ""
        )
        if not perguntar(
            self, "Excluir etiqueta", f"Excluir a etiqueta {etiqueta.nome}?{onde}", "Excluir"
        ):
            return
        excluir_etiqueta(self.base.conexao, etiqueta.id)
        self.base.salvar()
        self.mudou = True
        self.mostrar()
        confirmar_rapido(self, "Etiqueta excluída.")
