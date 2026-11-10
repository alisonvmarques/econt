"""Entidade · Contas: lista (T19), formulário (T20) e limites com pedido de alteração (T21)."""

from __future__ import annotations

from collections.abc import Callable
from contextlib import suppress
from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from econt.dados.banco import BaseDeDados
from econt.dados.contas import (
    ContaEntidade,
    DadosConta,
    cadastrar_conta,
    definir_ativa,
    editar_conta,
    listar_contas,
    obter_conta,
    problemas_da_conta,
    registrar_pedido,
)
from econt.dados.lista_bancos import listar_bancos
from econt.dominio.dinheiro import ValorInvalido, formatar_reais, ler_reais
from econt.dominio.limites import TIPOS_DE_LIMITE, PedidoInvalido, formatar_data_hora
from econt.interface.componentes import (
    Campo,
    CampoDataHora,
    CampoEscolha,
    Dialogo,
    EstadoVazio,
    Tabela,
    aviso,
    botao,
    cartao,
    confirmar_rapido,
    empilhar,
    etiqueta,
    linha_de_acoes,
    mudar_aviso,
    perguntar,
    texto,
)

Relogio = Callable[[], datetime]


def _agora() -> datetime:
    return datetime.now().replace(second=0, microsecond=0)


def texto_em_liberacao(conta: ContaEntidade, tipo: str) -> str | None:
    situacao = conta.pix if tipo == "pix" else conta.transacao
    pedido = situacao.em_liberacao
    if pedido is None:
        return None
    return (
        f"Limite {situacao.nome} em liberação: passa de {formatar_reais(situacao.vale_agora)} "
        f"para {formatar_reais(pedido.valor)} em {formatar_data_hora(pedido.liberado_em)}. "
        "Até lá, vale o atual."
    )


class DialogoConta(Dialogo):
    """T20 · Nova conta ou edição. Os limites não são editados aqui: mudam por pedido (RN11)."""

    def __init__(self, pai: QWidget | None, base: BaseDeDados, conta: ContaEntidade | None) -> None:
        titulo = "Editar conta da entidade" if conta else "Nova conta da entidade"
        super().__init__(pai, titulo, "Salvar conta")
        self.base = base
        self.conta = conta
        self.conta_id = conta.id if conta else None
        self.descricao = Campo("Descrição", "Um nome curto para reconhecer a conta.")
        bancos = [(b.codigo, b.rotulo) for b in listar_bancos(base.conexao)]
        self.banco = CampoEscolha("Banco", bancos, busca=True)
        self.agencia = Campo("Agência")
        self.numero = Campo("Conta com dígito")
        self.corpo.addWidget(self.descricao)
        self.corpo.addWidget(self.banco)
        linha = QHBoxLayout()
        linha.setSpacing(12)
        linha.addWidget(self.agencia)
        linha.addWidget(self.numero)
        self.corpo.addLayout(linha)
        if conta:
            self.descricao.definir(conta.descricao)
            self.banco.definir(conta.banco)
            self.agencia.definir(conta.agencia)
            self.numero.definir(conta.conta)
        else:
            self.banco.caixa.setCurrentIndex(-1)
            self.corpo.addWidget(
                texto(
                    "Conta nova começa com R$ 10.000,00 no limite Pix e no limite de transação.",
                    "ajuda",
                )
            )
        self.fechar_corpo()

    def dados(self) -> DadosConta:
        return DadosConta(
            self.descricao.valor(), self.banco.valor(), self.agencia.valor(), self.numero.valor()
        )

    def ao_confirmar(self) -> None:
        dados = self.dados()
        erros = problemas_da_conta(self.base.conexao, dados, ignorar_id=self.conta_id)
        campos = {
            "descricao": self.descricao,
            "banco": self.banco,
            "agencia": self.agencia,
            "conta": self.numero,
        }
        for chave, campo in campos.items():
            if chave in erros:
                campo.mostrar_erro(erros[chave])
            else:
                campo.limpar_erro()
        if erros:
            next(campos[c] for c in campos if c in erros).caixa.setFocus()
            return
        if self.conta_id is None:
            self.conta_id = cadastrar_conta(self.base.conexao, dados)
        else:
            editar_conta(self.base.conexao, self.conta_id, dados)
        self.base.salvar()
        self.accept()


class ListaContas(QWidget):
    """T19 · Contas da entidade com os limites que valem agora."""

    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 20, 0, 0)
        layout.setSpacing(16)
        topo = QHBoxLayout()
        topo.addWidget(
            texto("Contas de onde saem os pagamentos. Limites por conta e por dia.", "apoio"), 1
        )
        self.nova = botao("Nova conta", "principal")
        topo.addWidget(self.nova)
        layout.addLayout(topo)
        self.vazia = EstadoVazio(
            "Nenhuma conta da entidade",
            "Cadastre as contas de onde saem os pagamentos.",
            "Cadastrar conta",
        )
        self.vazia.acao.clicked.connect(lambda: self.nova.click())
        layout.addWidget(self.vazia, 0, Qt.AlignmentFlag.AlignHCenter)
        self.tabela = Tabela(
            ["Descrição", "Banco e conta", "Limite Pix (dia)", "Limite transação (dia)", "Situação"]
        )
        self.tabela.setWordWrap(False)
        cabecalho = self.tabela.horizontalHeader()
        cabecalho.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        cabecalho.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.tabela, 1)
        self.dica = texto(
            "Clique numa conta, ou use Enter, para ver os limites e pedir alteração.", "ajuda"
        )
        layout.addWidget(self.dica)
        layout.addStretch()

    def mostrar(self, contas: list[ContaEntidade]) -> None:
        self.vazia.setVisible(not contas)
        self.tabela.setVisible(bool(contas))
        self.dica.setVisible(bool(contas))
        self.tabela.setRowCount(len(contas))
        for linha, conta in enumerate(contas):
            self.tabela.celula(linha, 0, conta.descricao, conta.id)
            self.tabela.celula(linha, 1, conta.resumo)
            for coluna, situacao in ((2, conta.pix), (3, conta.transacao)):
                self.tabela.celula(linha, coluna, "")
                pecas = [texto(formatar_reais(situacao.vale_agora))]
                if situacao.em_liberacao:
                    pedido = situacao.em_liberacao
                    quando = pedido.liberado_em.strftime("%d/%m %H:%M")
                    pecas.append(
                        etiqueta(f"⏱ {formatar_reais(pedido.valor)} em {quando}", "atencao")
                    )
                self.tabela.setCellWidget(linha, coluna, empilhar(*pecas))
            self.tabela.celula(linha, 4, "")
            self.tabela.setCellWidget(
                linha, 4, empilhar(etiqueta("✓ Ativa" if conta.ativa else "Inativa"))
            )
        self.tabela.ajustar()


class DetalheConta(QWidget):
    """T21 · Limites da conta e pedido de alteração, com "em liberação até"."""

    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 20, 0, 0)
        layout.setSpacing(16)
        self.voltar = botao("← Todas as contas", "link")
        layout.addLayout(linha_de_acoes(self.voltar, alinhar="esquerda"))
        topo = QHBoxLayout()
        self.titulo = texto("", "secao")
        self.editar = botao("Editar conta")
        self.ativar = botao("Inativar conta")
        topo.addWidget(self.titulo, 1)
        topo.addWidget(self.editar)
        topo.addWidget(self.ativar)
        layout.addLayout(topo)
        self.situacao = aviso("", "info")
        layout.addWidget(self.situacao)
        self.avisos = QVBoxLayout()
        self.avisos.setSpacing(8)
        layout.addLayout(self.avisos)

        self.tabela = Tabela(["Limite", "Vale agora", "Pedido", "Situação"])
        self.tabela.setRowCount(2)
        self.tabela.setSelectionMode(Tabela.SelectionMode.NoSelection)
        self.tabela.setWordWrap(False)
        self.tabela.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tabela.horizontalHeader().setSectionResizeMode(
            3, QHeaderView.ResizeMode.ResizeToContents
        )

        layout.addWidget(self.tabela)

        self.formulario = cartao()
        interno = QVBoxLayout(self.formulario)
        interno.setContentsMargins(24, 20, 24, 20)
        interno.setSpacing(16)
        interno.addWidget(texto("Pedir alteração de limite", "secao"))
        grade = QGridLayout()
        grade.setHorizontalSpacing(12)
        self.tipo = CampoEscolha("Limite", list(TIPOS_DE_LIMITE.items()))
        self.valor = Campo("Novo valor", "Aumento ou redução.")
        self.pedido_em = CampoDataHora(
            "Data e hora do pedido", "Quando o pedido foi feito ao banco."
        )
        for coluna, campo in enumerate((self.tipo, self.valor, self.pedido_em)):
            grade.addWidget(campo, 0, coluna, Qt.AlignmentFlag.AlignTop)
            grade.setColumnStretch(coluna, 1)
        interno.addLayout(grade)
        interno.addWidget(
            texto("O novo valor só passa a valer 24 horas depois do pedido.", "ajuda")
        )
        self.retorno = aviso("", "sucesso")
        self.retorno.setVisible(False)
        interno.addWidget(self.retorno)
        self.registrar = botao("Registrar pedido", "principal")
        interno.addLayout(linha_de_acoes(self.registrar))
        layout.addWidget(self.formulario)
        layout.addStretch()
        self.valor.caixa.editingFinished.connect(self._formatar_valor)

    def _formatar_valor(self) -> None:
        with suppress(ValorInvalido):
            self.valor.definir(formatar_reais(ler_reais(self.valor.valor())))

    def mostrar(self, conta: ContaEntidade) -> None:
        self.titulo.setText(f"{conta.descricao} · {conta.resumo}")
        self.titulo.setToolTip(conta.banco_nome)
        self.ativar.setText("Inativar conta" if conta.ativa else "Reativar conta")
        self.ativar.setProperty("tipo", "perigo" if conta.ativa else "secundario")
        self.ativar.style().polish(self.ativar)
        self.situacao.setText(
            "ⓘ  Conta inativa: não aparece na Consulta. Os limites e os pedidos estão "
            "guardados; reative a conta para registrar pedidos."
        )
        self.situacao.setVisible(not conta.ativa)
        self.formulario.setEnabled(conta.ativa)
        while self.avisos.count():
            self.avisos.takeAt(0).widget().deleteLater()
        for tipo in TIPOS_DE_LIMITE:
            mensagem = texto_em_liberacao(conta, tipo)
            if mensagem:
                self.avisos.addWidget(aviso(mensagem, "atencao"))
        for linha, situacao in enumerate(conta.limites):
            self.tabela.celula(linha, 0, f"{situacao.nome} (por dia)")
            self.tabela.celula(linha, 1, formatar_reais(situacao.vale_agora))
            pedido = situacao.em_liberacao
            self.tabela.celula(linha, 2, formatar_reais(pedido.valor) if pedido else "—")
            self.tabela.celula(linha, 3, "")
            marca = (
                etiqueta(f"⏱ Em liberação até {formatar_data_hora(pedido.liberado_em)}", "atencao")
                if pedido
                else etiqueta("✓ Sem pedido")
            )
            self.tabela.setCellWidget(linha, 3, empilhar(marca))
        self.tabela.ajustar()
        altura = self.tabela.horizontalHeader().height() + sum(
            self.tabela.rowHeight(i) for i in range(2)
        )
        self.tabela.setFixedHeight(altura + 4)

    def limpar_formulario(self) -> None:
        self.valor.definir("")
        self.valor.limpar_erro()
        self.pedido_em.limpar_erro()
        self.pedido_em.definir(_agora())
        self.retorno.setVisible(False)


class PaginaContas(QStackedWidget):
    """Lista das contas e, ao escolher uma, os limites dela."""

    def __init__(self, base: BaseDeDados, relogio: Relogio = _agora) -> None:
        super().__init__()
        self.base = base
        self.relogio = relogio
        self.conta_aberta: int | None = None
        self.lista = ListaContas()
        self.detalhe = DetalheConta()
        self.addWidget(self.lista)
        self.addWidget(self.detalhe)
        self.lista.nova.clicked.connect(lambda: self.abrir_formulario(None))
        self.lista.tabela.escolhida.connect(
            lambda linha: self.abrir_conta(self.lista.tabela.dado_da_linha(linha))
        )
        self.detalhe.voltar.clicked.connect(self.voltar_para_lista)
        self.detalhe.editar.clicked.connect(lambda: self.abrir_formulario(self._conta()))
        self.detalhe.ativar.clicked.connect(self.trocar_ativa)
        self.detalhe.registrar.clicked.connect(self.registrar_pedido)
        self.detalhe.valor.caixa.returnPressed.connect(self.registrar_pedido)  # RNF05
        self.atualizar()

    def _conta(self) -> ContaEntidade:
        return obter_conta(self.base.conexao, self.conta_aberta, self.relogio())

    def showEvent(self, evento) -> None:  # noqa: N802 (nome do Qt)
        # Um pedido pode ter completado 24 horas desde a última vez que a tela foi vista.
        self.atualizar()
        super().showEvent(evento)

    def atualizar(self) -> None:
        self.lista.mostrar(listar_contas(self.base.conexao, self.relogio()))
        if self.conta_aberta is not None:
            self.detalhe.mostrar(self._conta())

    def criar_dialogo(self, conta: ContaEntidade | None) -> DialogoConta:
        return DialogoConta(self, self.base, conta)

    def abrir_formulario(self, conta: ContaEntidade | None) -> None:
        dialogo = self.criar_dialogo(conta)
        if dialogo.exec():
            self.abrir_conta(dialogo.conta_id)
            confirmar_rapido(self, "Conta salva.")

    def abrir_conta(self, conta_id: int) -> None:
        self.conta_aberta = conta_id
        self.detalhe.limpar_formulario()
        self.atualizar()
        self.setCurrentWidget(self.detalhe)
        self.detalhe.valor.caixa.setFocus()

    def voltar_para_lista(self) -> None:
        self.conta_aberta = None
        self.atualizar()
        self.setCurrentWidget(self.lista)
        self.lista.tabela.setFocus()

    def trocar_ativa(self) -> None:
        conta = self._conta()
        if conta.ativa and not perguntar(
            self,
            "Inativar conta",
            f"A conta {conta.descricao} deixa de aparecer na Consulta. Os limites, os pedidos "
            "e as marcações ficam guardados e voltam como estavam se a conta for reativada.",
            "Inativar conta",
        ):
            return
        definir_ativa(self.base.conexao, conta.id, not conta.ativa)
        self.base.salvar()
        self.atualizar()
        confirmar_rapido(self, "Conta inativada." if conta.ativa else "Conta reativada.")

    def registrar_pedido(self) -> None:
        detalhe = self.detalhe
        detalhe.retorno.setVisible(False)
        try:
            valor = ler_reais(detalhe.valor.valor())
        except ValorInvalido as erro:
            detalhe.valor.mostrar_erro(str(erro))
            detalhe.valor.caixa.setFocus()
            return
        tipo = detalhe.tipo.valor()
        try:
            pedido = registrar_pedido(
                self.base.conexao,
                self.conta_aberta,
                tipo,
                valor,
                detalhe.pedido_em.valor(),
                self.relogio(),
            )
        except PedidoInvalido as erro:
            campo = detalhe.pedido_em if "futuro" in str(erro) else detalhe.valor
            campo.mostrar_erro(str(erro))
            campo.caixa.setFocus()
            return
        self.base.salvar()
        self.atualizar()
        detalhe.limpar_formulario()
        nome = TIPOS_DE_LIMITE[tipo]
        mensagem = (
            f"Pedido registrado. O limite {nome} passa a {formatar_reais(pedido.valor)} "
            f"em {formatar_data_hora(pedido.liberado_em)}."
            if pedido.liberado_em > self.relogio()
            else f"Pedido registrado. O pedido já completou 24 horas: o limite {nome} já vale "
            f"{formatar_reais(pedido.valor)}."
        )
        mudar_aviso(detalhe.retorno, mensagem, "sucesso")
        detalhe.retorno.setVisible(True)
