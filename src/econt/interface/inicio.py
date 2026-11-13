"""Painel inicial (T07): resumo, atalhos e o que pede atenção (RF01, RF31)."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QGridLayout, QVBoxLayout, QWidget

from econt.dados.banco import BaseDeDados
from econt.dados.painel import Resumo, resumir
from econt.interface.componentes import aviso, botao, cartao, linha_de_acoes, texto


def _plural(n: int, um: str, varios: str) -> str:
    return um if n == 1 else varios


class Numero(QWidget):
    """Um número do resumo, com o que ele conta embaixo."""

    def __init__(self) -> None:
        super().__init__()
        self.quadro = cartao()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.quadro)
        interno = QVBoxLayout(self.quadro)
        interno.setContentsMargins(20, 18, 20, 18)
        interno.setSpacing(4)
        self.valor = texto("0", "titulo")
        self.rotulo = texto("", "ajuda")
        interno.addWidget(self.valor)
        interno.addWidget(self.rotulo)

    def mostrar(self, valor: int, rotulo: str) -> None:
        self.valor.setText(str(valor))
        self.rotulo.setText(rotulo)


class PaginaInicio(QWidget):
    ir = Signal(str)  # "consulta", "novo_fornecedor" ou "contas_entidade"

    def __init__(self, base: BaseDeDados) -> None:
        super().__init__()
        self.base = base
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 32, 40, 32)
        layout.setSpacing(16)
        layout.addWidget(texto("Início", "titulo"))
        layout.addWidget(texto("Resumo do que está cadastrado no ECont.", "apoio"))
        grade = QGridLayout()
        grade.setHorizontalSpacing(16)
        self.numeros = [Numero() for _ in range(4)]
        for coluna, numero in enumerate(self.numeros):
            grade.addWidget(numero, 0, coluna)
            grade.setColumnStretch(coluna, 1)
        layout.addLayout(grade)
        layout.addWidget(texto("Atalhos", "secao"))
        self.consultar = botao("Consultar fornecedor", "principal")
        self.novo_fornecedor = botao("Novo fornecedor")
        self.contas_entidade = botao("Contas da entidade")
        layout.addLayout(
            linha_de_acoes(
                self.consultar, self.novo_fornecedor, self.contas_entidade, alinhar="esquerda"
            )
        )
        self.titulo_atencao = texto("Atenção", "secao")
        layout.addWidget(self.titulo_atencao)
        self.atencao = QVBoxLayout()
        self.atencao.setSpacing(8)
        layout.addLayout(self.atencao)
        layout.addStretch()
        self.consultar.clicked.connect(lambda: self.ir.emit("consulta"))
        self.novo_fornecedor.clicked.connect(lambda: self.ir.emit("novo_fornecedor"))
        self.contas_entidade.clicked.connect(lambda: self.ir.emit("contas_entidade"))
        self.atualizar()

    def showEvent(self, evento) -> None:  # noqa: N802 (nome do Qt)
        self.atualizar()
        super().showEvent(evento)

    def atualizar(self) -> None:
        r: Resumo = resumir(self.base.conexao)
        liberando = len(r.limites_em_liberacao)
        self.numeros[0].mostrar(
            r.fornecedores_ativos,
            _plural(r.fornecedores_ativos, "fornecedor ativo", "fornecedores ativos"),
        )
        self.numeros[1].mostrar(
            r.contas_e_chaves,
            _plural(r.contas_e_chaves, "conta ou chave Pix", "contas e chaves Pix"),
        )
        self.numeros[2].mostrar(
            r.contas_entidade, _plural(r.contas_entidade, "conta da entidade", "contas da entidade")
        )
        self.numeros[3].mostrar(
            liberando, _plural(liberando, "limite em liberação", "limites em liberação")
        )
        while self.atencao.count():
            self.atencao.takeAt(0).widget().deleteLater()
        avisos = []
        if not r.contas_entidade:
            avisos.append(
                aviso(
                    "Comece pelas contas da entidade, de onde saem os pagamentos: "
                    "Entidade › Contas.",
                    "info",
                )
            )
        elif not r.fornecedores_ativos:
            avisos.append(
                aviso(
                    "Nenhum fornecedor ativo ainda. Cadastre o primeiro em Novo fornecedor.", "info"
                )
            )
        if r.sem_cadastro:
            avisos.append(
                aviso(
                    f"{r.sem_cadastro} "
                    + _plural(
                        r.sem_cadastro,
                        "conta ou chave Pix ativa não está cadastrada",
                        "contas ou chaves Pix ativas não estão cadastradas",
                    )
                    + " em nenhuma conta da entidade. Veja na aba Cadastros de cada fornecedor.",
                    "erro",
                )
            )
        if r.atividades_atrasadas:
            avisos.append(
                aviso(
                    f"{r.atividades_atrasadas} "
                    + _plural(r.atividades_atrasadas, "atividade atrasada", "atividades atrasadas")
                    + ". Veja em Atividades.",
                    "erro",
                )
            )
        if r.atividades_de_hoje:
            avisos.append(
                aviso(
                    f"{r.atividades_de_hoje} "
                    + _plural(
                        r.atividades_de_hoje, "atividade vence hoje", "atividades vencem hoje"
                    )
                    + ". Veja em Atividades.",
                    "atencao",
                )
            )
        avisos += [aviso(mensagem, "atencao") for mensagem in r.limites_em_liberacao]
        for item in avisos:
            self.atencao.addWidget(item)
        self.titulo_atencao.setVisible(bool(avisos))
