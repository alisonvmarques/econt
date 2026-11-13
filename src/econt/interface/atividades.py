"""Atividades (T28): o quadro da entidade, com colunas, cartões, busca e arrastar e soltar.

A tela nunca confia no que está desenhado: depois de qualquer mudança, recarrega o quadro da
base. Arrastar usa os recursos nativos do Qt; a coluna calcula antes de qual cartão o cartão
solto cai, e a posição real vem da ordem gravada (RN16), mesmo com a busca escondendo cartões.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date

from PySide6.QtCore import QMimeData, QPoint, Qt, Signal
from PySide6.QtGui import QDrag, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QScrollArea,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from econt.dados.atividades import (
    Atividade,
    ColunaDoQuadro,
    ColunaInvalida,
    arquivar_atividade,
    excluir_coluna,
    listar_colunas,
    mover_atividade,
    mover_coluna,
    obter_atividade,
    obter_coluna,
    obter_quadro,
)
from econt.dados.banco import BaseDeDados
from econt.dominio.atividades import ATRASADA, VENCE_HOJE, formatar_prazo, posicao_ao_soltar
from econt.interface.componentes import (
    avisar,
    botao,
    confirmar_rapido,
    etiqueta,
    perguntar,
    texto,
)
from econt.interface.dialogos_atividades import (
    DialogoArquivadas,
    DialogoAtividade,
    DialogoColuna,
    DialogoEtiquetas,
)

TIPO_ARRASTE = "application/x-econt-atividade"
LARGURA_COLUNA = 300
DESCRICAO = "As atividades da entidade, do que falta fazer ao que já foi concluído."

# Ações do cartão: (chave, rótulo no menu, atalho)
ACOES_DE_MOVER = [
    ("esquerda", "Mover para a coluna anterior", "Ctrl+Left"),
    ("direita", "Mover para a próxima coluna", "Ctrl+Right"),
    ("subir", "Subir na coluna", "Ctrl+Up"),
    ("descer", "Descer na coluna", "Ctrl+Down"),
]
_TECLAS = {
    Qt.Key.Key_Left: "esquerda",
    Qt.Key.Key_Right: "direita",
    Qt.Key.Key_Up: "subir",
    Qt.Key.Key_Down: "descer",
}

Hoje = Callable[[], date]


def _plural(n: int, um: str, varios: str) -> str:
    return um if n == 1 else varios


def texto_do_prazo(atividade: Atividade) -> tuple[str, str | None]:
    """Texto do prazo no cartão e o tipo de etiqueta (nenhuma quando é texto normal)."""
    if atividade.prazo is None:
        return "", None
    prazo = formatar_prazo(atividade.prazo)
    if atividade.situacao == ATRASADA:
        return f"⚠ Atrasada · prazo {prazo}", "perigo"
    if atividade.situacao == VENCE_HOJE:
        return "⏱ Vence hoje", "atencao"
    if atividade.concluida:
        return f"✓ Prazo {prazo}", None
    return f"Prazo {prazo}", None


# Prioridade no cartão: (texto, papel da etiqueta). A palavra diz a prioridade; a cor reforça.
MARCA_DA_PRIORIDADE = {
    3: ("▲ Alta", "perigo"),
    2: ("● Média", "atencao"),
    1: ("▼ Baixa", "neutra"),
}
LARGURA_UTIL_DO_CARTAO = LARGURA_COLUNA - 74  # margens da coluna, do cartão e a rolagem


def marcas_do_cartao(atividade: Atividade) -> list[tuple[str, str]]:
    """Prioridade (se houver) e depois as etiquetas, na ordem do nome."""
    marcas = []
    if atividade.prioridade in MARCA_DA_PRIORIDADE:
        marcas.append(MARCA_DA_PRIORIDADE[atividade.prioridade])
    marcas += [(e.nome, e.cor) for e in atividade.marcas]
    return marcas


def em_linhas(pecas: list[QWidget], largura: int, espaco: int = 4) -> QVBoxLayout:
    """Põe as peças lado a lado e passa para a linha de baixo quando não cabem."""
    linhas = QVBoxLayout()
    linhas.setSpacing(espaco)
    linha: QHBoxLayout | None = None
    usado = 0
    for peca in pecas:
        peca.ensurePolished()
        medida = peca.sizeHint().width()
        if linha is None or usado + medida > largura:
            if linha is not None:
                linha.addStretch()
            linha = QHBoxLayout()
            linha.setSpacing(espaco)
            linhas.addLayout(linha)
            usado = 0
        linha.addWidget(peca)
        usado += medida + espaco
    if linha is not None:
        linha.addStretch()
    return linhas


class CartaoAtividade(QFrame):
    """Um cartão do quadro. Enter ou duplo clique abrem; Ctrl+setas movem (RNF05)."""

    # "abrir", "esquerda", "direita", "subir", "descer", "arquivar", "arraste" e "fim_do_arraste"
    acao = Signal(str, int)

    def __init__(self, atividade: Atividade) -> None:
        super().__init__()
        self.atividade = atividade
        self.setObjectName("cartao_atividade")
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self.setProperty("prazo", atividade.situacao)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)
        self.titulo = texto(atividade.titulo)
        self.titulo.setStyleSheet("font-weight: 500;")
        layout.addWidget(self.titulo)
        partes = [atividade.titulo]
        self.marcas = [etiqueta(nome, tipo) for nome, tipo in marcas_do_cartao(atividade)]
        if self.marcas:
            layout.addLayout(em_linhas(self.marcas, LARGURA_UTIL_DO_CARTAO))
        if atividade.prioridade:
            partes.append(f"Prioridade {atividade.nome_da_prioridade.lower()}")
        if atividade.marcas:
            partes.append("Etiquetas " + ", ".join(e.nome for e in atividade.marcas))
        rotulo, tipo = texto_do_prazo(atividade)
        self.prazo: QLabel | None = None
        if rotulo:
            self.prazo = etiqueta(rotulo, tipo) if tipo else texto(rotulo, "ajuda")
            layout.addWidget(self.prazo, 0, Qt.AlignmentFlag.AlignLeft)
            partes.append(rotulo.lstrip("⚠⏱✓ "))
        self.fornecedor: QLabel | None = None
        if atividade.fornecedor_nome:
            nome = atividade.fornecedor_nome
            if not atividade.fornecedor_ativo:
                nome += " (inativo)"
            self.fornecedor = texto(nome, "ajuda")
            layout.addWidget(self.fornecedor)
            partes.append(f"Fornecedor {nome}")
        self.setAccessibleName(". ".join(partes))
        self.setToolTip(
            "Enter ou duplo clique abre. Arraste ou use Ctrl+setas para mover. "
            "Menu com o botão direito."
        )
        self._inicio_do_arraste: QPoint | None = None

    @property
    def id(self) -> int:
        return self.atividade.id

    def keyPressEvent(self, evento) -> None:  # noqa: N802 (nome do Qt)
        controle = evento.modifiers() & Qt.KeyboardModifier.ControlModifier
        if controle and evento.key() in _TECLAS:
            self.acao.emit(_TECLAS[evento.key()], self.id)
            return
        if evento.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space):
            self.acao.emit("abrir", self.id)
            return
        super().keyPressEvent(evento)

    def mouseDoubleClickEvent(self, evento) -> None:  # noqa: N802 (nome do Qt)
        self.acao.emit("abrir", self.id)

    def mousePressEvent(self, evento) -> None:  # noqa: N802 (nome do Qt)
        if evento.button() == Qt.MouseButton.LeftButton:
            self._inicio_do_arraste = evento.position().toPoint()
            self.setFocus()
        super().mousePressEvent(evento)

    def mouseMoveEvent(self, evento) -> None:  # noqa: N802 (nome do Qt)
        if (
            self._inicio_do_arraste is not None
            and evento.buttons() & Qt.MouseButton.LeftButton
            and (evento.position().toPoint() - self._inicio_do_arraste).manhattanLength()
            >= QApplication.startDragDistance()
        ):
            self._inicio_do_arraste = None
            self.arrastar()
            return
        super().mouseMoveEvent(evento)

    def dados_do_arraste(self) -> QMimeData:
        dados = QMimeData()
        dados.setData(TIPO_ARRASTE, str(self.id).encode())
        return dados

    def arrastar(self) -> None:
        arraste = QDrag(self)
        arraste.setMimeData(self.dados_do_arraste())
        arraste.setPixmap(self.grab())
        arraste.setHotSpot(QPoint(20, 12))
        self.acao.emit("arraste", self.id)
        arraste.exec(Qt.DropAction.MoveAction)
        self.acao.emit("fim_do_arraste", self.id)

    def criar_menu(self) -> QMenu:
        menu = QMenu(self)
        menu.addAction("Abrir", lambda: self.acao.emit("abrir", self.id))
        menu.addSeparator()
        for chave, rotulo, atalho in ACOES_DE_MOVER:
            item = menu.addAction(rotulo, lambda c=chave: self.acao.emit(c, self.id))
            item.setShortcut(QKeySequence(atalho))
        menu.addSeparator()
        menu.addAction("Arquivar…", lambda: self.acao.emit("arquivar", self.id))
        return menu

    def contextMenuEvent(self, evento) -> None:  # noqa: N802 (nome do Qt)
        self.criar_menu().exec(evento.globalPos())


class ColunaQuadro(QFrame):
    """Uma coluna: cabeçalho com nome e quantidade, os cartões e Nova atividade."""

    soltado = Signal(int, int, object)  # atividade, coluna, antes de qual atividade (ou None)
    nova = Signal(int)
    opcao = Signal(str, int)  # "editar", "esquerda", "direita", "excluir"

    def __init__(self, item: ColunaDoQuadro, primeira: bool, ultima: bool) -> None:
        super().__init__()
        self.coluna = item.coluna
        self.ordem = [a.id for a in item.atividades]  # a ordem real, gravada na base
        self.setObjectName("coluna_quadro")
        self.setFixedWidth(LARGURA_COLUNA)
        self.setAcceptDrops(True)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 12, 10, 10)
        layout.setSpacing(8)

        cabecalho = QHBoxLayout()
        cabecalho.setContentsMargins(4, 0, 0, 0)
        self.nome = texto(self.coluna.nome, "secao")
        self.nome.setStyleSheet("font-size: 15px;")
        self.quantidade = etiqueta("0")
        cabecalho.addWidget(self.nome, 1)
        if self.coluna.conclusao:
            marca = etiqueta("✓ Conclusão", "sucesso")
            marca.setToolTip("Atividade nesta coluna conta como concluída.")
            marca.ensurePolished()  # com as margens do tema, a etiqueta não sai cortada
            marca.setMinimumWidth(marca.sizeHint().width())
            cabecalho.addWidget(marca)
        cabecalho.addWidget(self.quantidade)
        self.opcoes = QToolButton()
        self.opcoes.setText("⋯")
        self.opcoes.setProperty("papel", "opcoes")
        self.opcoes.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.opcoes.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.opcoes.setAccessibleName(f"Opções da coluna {self.coluna.nome}")
        self.opcoes.setToolTip("Editar, mover ou excluir a coluna")
        self.menu = QMenu(self.opcoes)
        self.menu.addAction("Editar coluna…", lambda: self.opcao.emit("editar", self.coluna.id))
        esquerda = self.menu.addAction(
            "Mover para a esquerda", lambda: self.opcao.emit("esquerda", self.coluna.id)
        )
        direita = self.menu.addAction(
            "Mover para a direita", lambda: self.opcao.emit("direita", self.coluna.id)
        )
        esquerda.setEnabled(not primeira)
        direita.setEnabled(not ultima)
        self.menu.addSeparator()
        self.menu.addAction("Excluir coluna…", lambda: self.opcao.emit("excluir", self.coluna.id))
        self.opcoes.setMenu(self.menu)
        cabecalho.addWidget(self.opcoes)
        layout.addLayout(cabecalho)

        self.rolagem = QScrollArea()
        self.rolagem.setWidgetResizable(True)
        self.rolagem.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.rolagem.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.lista = QWidget()
        self.lista_layout = QVBoxLayout(self.lista)
        self.lista_layout.setContentsMargins(2, 2, 2, 2)
        self.lista_layout.setSpacing(8)
        self.cartoes: list[CartaoAtividade] = []
        for atividade in item.atividades:
            cartao = CartaoAtividade(atividade)
            self.cartoes.append(cartao)
            self.lista_layout.addWidget(cartao)
        self.vazia = texto("Nenhuma atividade nesta coluna.", "ajuda")
        self.vazia.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lista_layout.addWidget(self.vazia)
        self.lista_layout.addStretch()
        self.rolagem.setWidget(self.lista)
        layout.addWidget(self.rolagem, 1)

        self.indicador = QFrame(self.lista)
        self.indicador.setObjectName("indicador_soltar")
        self.indicador.setFixedHeight(4)
        self.indicador.hide()
        self.antes_de_indicado: int | None = None

        self.nova_atividade = botao("+ Nova atividade")
        self.nova_atividade.setAccessibleName(f"Nova atividade em {self.coluna.nome}")
        self.nova_atividade.clicked.connect(lambda: self.nova.emit(self.coluna.id))
        layout.addWidget(self.nova_atividade)
        self.filtrar("")

    # Busca --------------------------------------------------------------------------------

    def filtrar(self, busca: str) -> int:
        """Mostra só os cartões que combinam com a busca. Devolve quantos ficaram à mostra."""
        visiveis = 0
        for cartao in self.cartoes:
            combina = cartao.atividade.combina(busca)
            cartao.setVisible(combina)
            visiveis += combina
        total = len(self.cartoes)
        filtrando = bool(busca.strip())
        self.quantidade.setText(f"{visiveis} de {total}" if filtrando else str(total))
        self.quantidade.setToolTip(
            f"{total} {_plural(total, 'atividade', 'atividades')} nesta coluna"
        )
        if not total:
            self.vazia.setText("Nenhuma atividade nesta coluna.")
        elif not visiveis:
            self.vazia.setText("Nenhuma atividade encontrada nesta coluna.")
        self.vazia.setVisible(not visiveis)
        return visiveis

    def visiveis(self) -> list[CartaoAtividade]:
        return [c for c in self.cartoes if not c.isHidden()]

    def antes_de_vizinho(self, atividade_id: int, passo: int) -> tuple[bool, int | None]:
        """Para subir ou descer pelo teclado: antes de qual atividade o cartão deve ir.
        Pula os cartões escondidos pela busca, para o movimento ser visível."""
        ids = [c.id for c in self.visiveis()]
        if atividade_id not in ids:
            return False, None
        indice = ids.index(atividade_id)
        if passo < 0:
            return (True, ids[indice - 1]) if indice > 0 else (False, None)
        if indice + 1 >= len(ids):
            return False, None
        return True, self._seguinte_na_ordem(ids[indice + 1])

    def _seguinte_na_ordem(self, atividade_id: int) -> int | None:
        posicao = self.ordem.index(atividade_id)
        return self.ordem[posicao + 1] if posicao + 1 < len(self.ordem) else None

    # Arrastar e soltar --------------------------------------------------------------------

    def antes_de(self, ponto: QPoint) -> int | None:
        """Antes de qual atividade cai um cartão solto neste ponto (na coordenada da coluna).

        Abaixo do último cartão à mostra, cai logo depois dele na ordem real."""
        y = self.lista.mapFrom(self, ponto).y()
        visiveis = self.visiveis()
        for cartao in visiveis:
            if y < cartao.geometry().center().y():
                return cartao.id
        return self._seguinte_na_ordem(visiveis[-1].id) if visiveis else None

    def mostrar_indicador(self, antes_de: int | None) -> None:
        """Linha onde o cartão vai cair."""
        self.antes_de_indicado = antes_de
        visiveis = self.visiveis()
        alvo = next((c for c in visiveis if c.id == antes_de), None)
        espaco = self.lista_layout.spacing()
        if alvo is not None:
            y = alvo.geometry().top() - espaco // 2 - 2
        elif visiveis:
            y = visiveis[-1].geometry().bottom() + espaco // 2 - 1
        else:
            y = self.vazia.geometry().top()
        margem = self.lista_layout.contentsMargins().left()
        self.indicador.setGeometry(margem, max(0, y), self.lista.width() - 2 * margem, 4)
        self.indicador.raise_()
        self.indicador.show()

    def esconder_indicador(self) -> None:
        self.indicador.hide()
        self.antes_de_indicado = None

    @staticmethod
    def _atividade_do_arraste(dados: QMimeData) -> int | None:
        if not dados.hasFormat(TIPO_ARRASTE):
            return None
        try:
            return int(bytes(dados.data(TIPO_ARRASTE)).decode())
        except ValueError:
            return None

    def dragEnterEvent(self, evento) -> None:  # noqa: N802 (nome do Qt)
        if self._atividade_do_arraste(evento.mimeData()) is not None:
            evento.acceptProposedAction()
        else:
            evento.ignore()

    def dragMoveEvent(self, evento) -> None:  # noqa: N802 (nome do Qt)
        if self._atividade_do_arraste(evento.mimeData()) is None:
            evento.ignore()
            return
        self.mostrar_indicador(self.antes_de(evento.position().toPoint()))
        evento.acceptProposedAction()

    def dragLeaveEvent(self, evento) -> None:  # noqa: N802 (nome do Qt)
        self.esconder_indicador()
        super().dragLeaveEvent(evento)

    def dropEvent(self, evento) -> None:  # noqa: N802 (nome do Qt)
        atividade_id = self._atividade_do_arraste(evento.mimeData())
        self.esconder_indicador()
        if atividade_id is None:
            evento.ignore()
            return
        antes = self.antes_de(evento.position().toPoint())
        evento.setDropAction(Qt.DropAction.MoveAction)
        evento.accept()
        self.soltado.emit(atividade_id, self.coluna.id, antes)


class PaginaAtividades(QWidget):
    """T28 · O quadro de atividades da entidade (RF27 a RF30)."""

    def __init__(self, base: BaseDeDados, hoje: Hoje = date.today) -> None:
        super().__init__()
        self.base = base
        self.hoje = hoje
        self.colunas: list[ColunaQuadro] = []
        # Durante um arraste, o quadro só é remontado quando ele termina: o cartão arrastado
        # não pode ser destruído enquanto o Qt ainda cuida do arraste dele.
        self.arrastando = False
        self.foco_depois_do_arraste: int | None = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 32, 40, 32)
        layout.setSpacing(16)
        layout.addWidget(texto("Atividades", "titulo"))
        layout.addWidget(texto(DESCRICAO, "apoio"))

        topo = QHBoxLayout()
        topo.setSpacing(12)
        self.busca = QLineEdit()
        self.busca.setPlaceholderText("Buscar por título, descrição, fornecedor ou etiqueta")
        self.busca.setAccessibleName("Buscar atividades")
        self.busca.setClearButtonEnabled(True)
        self.busca.setMaximumWidth(420)
        self.nova_coluna = botao("Nova coluna")
        self.arquivadas = botao("Mostrar arquivadas")
        self.etiquetas = botao("Etiquetas")
        self.etiquetas.setToolTip("Criar, mudar e excluir as etiquetas")
        topo.addWidget(self.busca, 1)
        topo.addStretch()
        topo.addWidget(self.nova_coluna)
        topo.addWidget(self.etiquetas)
        topo.addWidget(self.arquivadas)
        layout.addLayout(topo)

        self.apoio = texto("", "apoio")
        layout.addWidget(self.apoio)

        self.rolagem = QScrollArea()
        self.rolagem.setWidgetResizable(True)
        self.rolagem.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.rolagem.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.faixa = QWidget()
        self.faixa_layout = QHBoxLayout(self.faixa)
        self.faixa_layout.setContentsMargins(0, 0, 0, 8)
        self.faixa_layout.setSpacing(16)
        self.faixa_layout.addStretch()
        self.rolagem.setWidget(self.faixa)
        layout.addWidget(self.rolagem, 1)

        self.busca.textChanged.connect(self.filtrar)
        self.busca.returnPressed.connect(self._focar_primeiro)
        self.nova_coluna.clicked.connect(lambda: self.editar_coluna(None))
        self.arquivadas.clicked.connect(self.mostrar_arquivadas)
        self.etiquetas.clicked.connect(self.mostrar_etiquetas)
        self.atualizar()

    def showEvent(self, evento) -> None:  # noqa: N802 (nome do Qt)
        # O dia pode ter virado e um fornecedor pode ter mudado de nome desde a última vez.
        self.atualizar()
        super().showEvent(evento)

    # Montagem -----------------------------------------------------------------------------

    def atualizar(self, foco: int | None = None) -> None:
        """Remonta o quadro a partir da base e, se pedido, põe o foco num cartão."""
        for coluna in self.colunas:
            self.faixa_layout.removeWidget(coluna)
            coluna.hide()
            coluna.deleteLater()
        quadro = obter_quadro(self.base.conexao, self.hoje())
        self.colunas = []
        for indice, item in enumerate(quadro):
            coluna = ColunaQuadro(item, indice == 0, indice == len(quadro) - 1)
            coluna.soltado.connect(self.soltar)
            coluna.nova.connect(self.nova_atividade)
            coluna.opcao.connect(self._opcao_da_coluna)
            for cartao in coluna.cartoes:
                cartao.acao.connect(self._acao_do_cartao)
            self.faixa_layout.insertWidget(indice, coluna)
            self.colunas.append(coluna)
        self.filtrar(self.busca.text())
        if foco is not None:
            self.focar(foco)

    def filtrar(self, busca: str) -> None:
        total = sum(len(c.cartoes) for c in self.colunas)
        visiveis = sum(c.filtrar(busca) for c in self.colunas)
        if not total:
            self.apoio.setText(
                "Nenhuma atividade ainda. Use Nova atividade numa coluna para começar."
            )
        elif busca.strip() and not visiveis:
            self.apoio.setText(f"Nenhuma atividade encontrada para “{busca.strip()}”.")
        else:
            self.apoio.setText(
                "Arraste os cartões ou use Ctrl+setas para mover. Enter abre a atividade."
            )

    def cartao(self, atividade_id: int) -> CartaoAtividade | None:
        for coluna in self.colunas:
            for cartao in coluna.cartoes:
                if cartao.id == atividade_id:
                    return cartao
        return None

    def coluna(self, coluna_id: int) -> ColunaQuadro:
        return next(c for c in self.colunas if c.coluna.id == coluna_id)

    def focar(self, atividade_id: int) -> None:
        cartao = self.cartao(atividade_id)
        if cartao is None or cartao.isHidden():
            return
        cartao.setFocus()
        coluna = cartao.parentWidget()
        while coluna is not None and not isinstance(coluna, ColunaQuadro):
            coluna = coluna.parentWidget()
        if coluna is not None:
            coluna.rolagem.ensureWidgetVisible(cartao)
            self.rolagem.ensureWidgetVisible(coluna)

    def _focar_primeiro(self) -> None:
        for coluna in self.colunas:
            if visiveis := coluna.visiveis():
                visiveis[0].setFocus()
                return

    # Atividades ---------------------------------------------------------------------------

    def _acao_do_cartao(self, acao: str, atividade_id: int) -> None:
        if acao == "arraste":
            self.arrastando, self.foco_depois_do_arraste = True, atividade_id
        elif acao == "fim_do_arraste":
            self.arrastando = False
            self.atualizar(foco=self.foco_depois_do_arraste)
        elif acao == "abrir":
            self.abrir_atividade(atividade_id)
        elif acao == "arquivar":
            self.arquivar(atividade_id)
        elif acao in ("esquerda", "direita"):
            self.mover_de_coluna(atividade_id, -1 if acao == "esquerda" else 1)
        else:
            self.mover_na_coluna(atividade_id, -1 if acao == "subir" else 1)

    def criar_dialogo_atividade(self, coluna_id: int, atividade_id: int | None) -> DialogoAtividade:
        atividade = (
            obter_atividade(self.base.conexao, atividade_id, self.hoje()) if atividade_id else None
        )
        coluna = obter_coluna(self.base.conexao, atividade.coluna_id if atividade else coluna_id)
        return DialogoAtividade(self, self.base, coluna, atividade)

    def nova_atividade(self, coluna_id: int) -> None:
        dialogo = self.criar_dialogo_atividade(coluna_id, None)
        if dialogo.exec():
            self.atualizar(foco=dialogo.atividade_id)
            confirmar_rapido(self, "Atividade criada.")

    def abrir_atividade(self, atividade_id: int) -> None:
        dialogo = self.criar_dialogo_atividade(0, atividade_id)
        if not dialogo.exec():
            self.focar(atividade_id)
            return
        if dialogo.pediu_arquivar:
            self.arquivar(atividade_id)
            return
        self.atualizar(foco=atividade_id)
        confirmar_rapido(self, "Atividade salva.")

    def arquivar(self, atividade_id: int) -> None:
        atividade = obter_atividade(self.base.conexao, atividade_id)
        if not perguntar(
            self,
            "Arquivar atividade",
            f"Arquivar a atividade {atividade.titulo}? Ela sai do quadro, mas fica guardada "
            "em Mostrar arquivadas e pode ser restaurada.",
            "Arquivar",
        ):
            self.focar(atividade_id)
            return
        # O foco vai para o cartão de baixo (ou o de cima), para seguir pelo teclado.
        ids = [c.id for c in self.coluna(atividade.coluna_id).visiveis()]
        vizinhos = ids[ids.index(atividade_id) + 1 :] + ids[: ids.index(atividade_id)][::-1]
        arquivar_atividade(self.base.conexao, atividade_id)
        self.base.salvar()
        vizinho = vizinhos[0] if vizinhos else None
        self.atualizar(foco=vizinho)
        if vizinho is None:
            self.coluna(atividade.coluna_id).nova_atividade.setFocus()
        confirmar_rapido(self, "Atividade arquivada.")

    def mover(self, atividade_id: int, coluna_id: int, posicao: int) -> None:
        """Grava na base, salva no disco e redesenha a partir do que foi gravado."""
        try:
            mover_atividade(self.base.conexao, atividade_id, coluna_id, posicao)
        except ValueError as erro:
            avisar(self, "Não foi possível mover", str(erro))
            if not self.arrastando:
                self.atualizar()
            return
        self.base.salvar()
        if self.arrastando:
            self.foco_depois_do_arraste = atividade_id
        else:
            self.atualizar(foco=atividade_id)

    def soltar(self, atividade_id: int, coluna_id: int, antes_de: int | None) -> None:
        ordem = self.coluna(coluna_id).ordem
        self.mover(atividade_id, coluna_id, posicao_ao_soltar(ordem, atividade_id, antes_de))

    def mover_de_coluna(self, atividade_id: int, passo: int) -> None:
        """Ctrl+← e Ctrl+→: para o fim da coluna vizinha."""
        ids = [c.coluna.id for c in self.colunas]
        atual = obter_atividade(self.base.conexao, atividade_id).coluna_id
        destino = ids.index(atual) + passo
        if 0 <= destino < len(ids):
            ordem = self.colunas[destino].ordem
            self.mover(atividade_id, ids[destino], len(ordem) + 1)

    def mover_na_coluna(self, atividade_id: int, passo: int) -> None:
        """Ctrl+↑ e Ctrl+↓: troca de lugar com o cartão de cima ou de baixo."""
        atividade = obter_atividade(self.base.conexao, atividade_id)
        coluna = self.coluna(atividade.coluna_id)
        pode, antes = coluna.antes_de_vizinho(atividade_id, passo)
        if pode:
            self.soltar(atividade_id, coluna.coluna.id, antes)

    def mostrar_etiquetas(self) -> None:
        dialogo = DialogoEtiquetas(self, self.base)
        dialogo.exec()
        if dialogo.mudou:
            self.atualizar()

    def mostrar_arquivadas(self) -> None:
        dialogo = DialogoArquivadas(self, self.base)
        dialogo.exec()
        if dialogo.mudou:
            self.atualizar()

    # Colunas ------------------------------------------------------------------------------

    def _opcao_da_coluna(self, opcao: str, coluna_id: int) -> None:
        if opcao == "editar":
            self.editar_coluna(coluna_id)
        elif opcao == "excluir":
            self.excluir_coluna(coluna_id)
        else:
            self.mover_coluna(coluna_id, -1 if opcao == "esquerda" else 1)

    def criar_dialogo_coluna(self, coluna_id: int | None) -> DialogoColuna:
        coluna = obter_coluna(self.base.conexao, coluna_id) if coluna_id else None
        return DialogoColuna(self, self.base, coluna)

    def editar_coluna(self, coluna_id: int | None) -> None:
        dialogo = self.criar_dialogo_coluna(coluna_id)
        if dialogo.exec():
            self.atualizar()
            self.coluna(dialogo.coluna_id).opcoes.setFocus()
            confirmar_rapido(self, "Coluna salva.")

    def mover_coluna(self, coluna_id: int, passo: int) -> None:
        posicao = obter_coluna(self.base.conexao, coluna_id).posicao + passo
        mover_coluna(self.base.conexao, coluna_id, posicao)
        self.base.salvar()
        self.atualizar()
        self.coluna(coluna_id).opcoes.setFocus()

    def excluir_coluna(self, coluna_id: int) -> None:
        coluna = obter_coluna(self.base.conexao, coluna_id)
        if len(listar_colunas(self.base.conexao)) > 1 and not self.coluna(coluna_id).ordem:
            confirmado = perguntar(
                self,
                "Excluir coluna",
                f"Excluir a coluna {coluna.nome}? As outras colunas e as atividades delas "
                "não mudam.",
                "Excluir coluna",
            )
            if not confirmado:
                return
        try:
            excluir_coluna(self.base.conexao, coluna_id)
        except ColunaInvalida as erro:
            avisar(self, "Não dá para excluir a coluna", str(erro))
            return
        self.base.salvar()
        self.atualizar()
        confirmar_rapido(self, "Coluna excluída.")
