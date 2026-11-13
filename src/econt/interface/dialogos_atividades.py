"""Atividades: diálogos da atividade (T29), das arquivadas (T30) e da coluna (T31)."""

from __future__ import annotations

from datetime import date

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCheckBox, QHBoxLayout, QHeaderView, QPlainTextEdit, QWidget

from econt.dados.atividades import (
    Atividade,
    Coluna,
    ColunaInvalida,
    DadosAtividade,
    coluna_de_conclusao,
    criar_atividade,
    criar_coluna,
    definir_conclusao,
    editar_atividade,
    excluir_atividade,
    listar_arquivadas,
    problema_da_coluna,
    problemas_da_atividade,
    renomear_coluna,
    restaurar_atividade,
)
from econt.dados.banco import BaseDeDados
from econt.dados.fornecedores import listar_fornecedores
from econt.dominio.atividades import (
    TAMANHO_DO_NOME_DA_COLUNA,
    TAMANHO_DO_TITULO,
    AtividadeInvalida,
    formatar_prazo,
    ler_prazo,
)
from econt.interface.componentes import (
    Campo,
    CampoBase,
    CampoEscolha,
    Dialogo,
    Tabela,
    botao,
    confirmar_rapido,
    linha_de_acoes,
    perguntar,
    texto,
)

SEM_FORNECEDOR = 0


def _data_hora(momento) -> str:
    return momento.strftime("%d/%m/%Y às %H:%M") if momento else ""


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
        opcoes = [(SEM_FORNECEDOR, "Sem fornecedor")]
        for f in listar_fornecedores(base.conexao):
            opcoes.append((f.id, self._nome_do_fornecedor(f.razao_social, f.nome_fantasia)))
        if atividade and atividade.fornecedor_id and not atividade.fornecedor_ativo:
            nome = self._nome_do_fornecedor(
                atividade.fornecedor_razao_social, atividade.fornecedor_nome
            )
            opcoes.append((atividade.fornecedor_id, f"{nome} (inativo)"))
        self.fornecedor = CampoEscolha(
            "Fornecedor", opcoes, "Opcional. Digite parte do nome para filtrar.", busca=True
        )
        self.fornecedor.caixa.lineEdit().setPlaceholderText("Sem fornecedor")
        for campo in (self.titulo, self.descricao):
            self.corpo.addWidget(campo)
        linha = QHBoxLayout()
        linha.setSpacing(12)
        linha.addWidget(self.prazo, 1, Qt.AlignmentFlag.AlignTop)
        linha.addWidget(self.fornecedor, 2, Qt.AlignmentFlag.AlignTop)
        self.corpo.addLayout(linha)

        if atividade:
            self.titulo.definir(atividade.titulo)
            self.descricao.caixa.setPlainText(atividade.descricao)
            self.prazo.definir(formatar_prazo(atividade.prazo))
            self.fornecedor.definir(atividade.fornecedor_id or SEM_FORNECEDOR)
            datas = [f"Na coluna {atividade.coluna_nome}."]
            datas.append(f"Criada em {_data_hora(atividade.criado_em)}.")
            if atividade.alterado_em != atividade.criado_em:
                datas.append(f"Alterada em {_data_hora(atividade.alterado_em)}.")
            if atividade.movido_em != atividade.criado_em:
                datas.append(f"Mudou de coluna em {_data_hora(atividade.movido_em)}.")
            self.datas = texto(" ".join(datas), "ajuda")
            self.corpo.addWidget(self.datas)
        else:
            self.fornecedor.definir(SEM_FORNECEDOR)
        self.fornecedor.caixa.lineEdit().setCursorPosition(0)  # o começo do nome à mostra

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
        valor = self.fornecedor.valor()
        if valor == "":
            return ""
        return valor or None

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
            self.titulo.valor(), self.descricao.caixa.toPlainText(), prazo, fornecedor
        )
        erros = problemas_da_atividade(self.base.conexao, dados) | erros
        campos = {"titulo": self.titulo, "prazo": self.prazo, "fornecedor": self.fornecedor}
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
