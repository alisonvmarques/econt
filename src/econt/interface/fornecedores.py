"""Fornecedores: lista (T10), formulário (T11), ficha com abas (T12, T13), conta bancária
(T14), chave Pix (T15) e confirmações (T17)."""

from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLineEdit,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from econt.dados.banco import BaseDeDados
from econt.dados.entidade import obter_entidade
from econt.dados.fornecedores import (
    TIPOS_DE_CONTA,
    ChavePix,
    ContaFornecedor,
    DadosContaFornecedor,
    DadosFornecedor,
    Fornecedor,
    cadastrar_fornecedor,
    definir_fornecedor_ativo,
    definir_item_ativo,
    editar_fornecedor,
    excluir_fornecedor,
    excluir_item,
    item_tem_historico,
    listar_chaves,
    listar_contas_fornecedor,
    listar_fornecedores,
    obter_fornecedor,
    outros_fornecedores_com_a_chave,
    outros_fornecedores_com_a_conta,
    problema_da_chave,
    problemas_da_conta_fornecedor,
    problemas_do_fornecedor,
    salvar_chave_pix,
    salvar_conta_fornecedor,
    tem_historico,
)
from econt.dados.lista_bancos import listar_bancos
from econt.dominio.documentos import TIPOS_DE_PESSOA, formatar_documento
from econt.dominio.formatos import (
    chave_pix_ao_digitar,
    documento_ao_digitar,
    telefone_ao_digitar,
)
from econt.dominio.pix import TIPOS_DE_CHAVE
from econt.interface.cadastros import PainelCadastros
from econt.interface.componentes import (
    Abas,
    Campo,
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
    formatar_ao_digitar,
    linha_de_acoes,
    mudar_aviso,
    perguntar,
    texto,
)
from econt.interface.impressao import abrir_janela_impressao
from econt.interface.impressoes import ficha_completa

MARGENS = (40, 32, 40, 32)


def _data(iso: str) -> str:
    return datetime.fromisoformat(iso).strftime("%d/%m/%Y") if iso else "—"


def _situacao(ativo: bool, feminino: bool = False) -> QWidget:
    rotulo = (
        ("✓ Ativa" if feminino else "✓ Ativo") if ativo else ("Inativa" if feminino else "Inativo")
    )
    return empilhar(etiqueta(rotulo))


def _lista_de_nomes(nomes: list[str]) -> str:
    return nomes[0] if len(nomes) == 1 else ", ".join(nomes[:-1]) + " e " + nomes[-1]


# Lista ------------------------------------------------------------------------------------


class ListaFornecedores(QWidget):
    """T10 · Lista com busca por nome e CNPJ/CPF."""

    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(*MARGENS)
        layout.setSpacing(16)
        layout.addWidget(texto("Fornecedores", "titulo"))
        topo = QHBoxLayout()
        topo.setSpacing(12)
        self.busca = QLineEdit()
        self.busca.setPlaceholderText("Buscar por nome ou CNPJ/CPF")
        self.busca.setAccessibleName("Buscar fornecedor")
        self.busca.setClearButtonEnabled(True)
        self.novo = botao("Novo fornecedor", "principal")
        topo.addWidget(self.busca, 1)
        topo.addWidget(self.novo)
        layout.addLayout(topo)
        self.inativos = QCheckBox("Mostrar inativos")
        layout.addWidget(self.inativos)
        self.vazia = EstadoVazio(
            "Nenhum fornecedor cadastrado",
            "Os fornecedores e as contas deles aparecem aqui.",
            "Cadastrar o primeiro fornecedor",
        )
        self.vazia.acao.clicked.connect(lambda: self.novo.click())
        layout.addWidget(self.vazia, 0, Qt.AlignmentFlag.AlignHCenter)
        self.tabela = Tabela(["Razão social", "CNPJ/CPF", "Contas e Pix", "Situação"])
        self.tabela.setWordWrap(False)
        cabecalho = self.tabela.horizontalHeader()
        cabecalho.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        cabecalho.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.tabela, 1)
        layout.addStretch()

    def mostrar(self, fornecedores: list[Fornecedor], buscando: bool) -> None:
        self.tabela.setVisible(bool(fornecedores))
        self.vazia.setVisible(not fornecedores)
        if buscando:
            self.vazia.mudar(
                "Nenhum fornecedor encontrado",
                "Confira a grafia ou busque pelo CNPJ ou CPF.",
            )
        elif self.inativos.isChecked():
            self.vazia.mudar("Nenhum fornecedor cadastrado", "Cadastre o primeiro fornecedor.")
        else:
            self.vazia.mudar(
                "Nenhum fornecedor cadastrado",
                "Os fornecedores e as contas deles aparecem aqui.",
            )
        self.vazia.acao.setVisible(not buscando)
        self.tabela.setRowCount(len(fornecedores))
        for linha, f in enumerate(fornecedores):
            self.tabela.celula(linha, 0, f.razao_social, f.id)
            self.tabela.celula(linha, 1, f.documento_formatado)
            self.tabela.celula(linha, 2, str(f.contas_e_chaves))
            self.tabela.celula(linha, 3, "")
            self.tabela.setCellWidget(linha, 3, _situacao(f.ativo))
        self.tabela.ajustar()


# Formulário -------------------------------------------------------------------------------


class FormularioFornecedor(QWidget):
    """T11 · Novo fornecedor e edição."""

    salvo = Signal(int)
    cancelado = Signal()

    def __init__(self, base: BaseDeDados) -> None:
        super().__init__()
        self.base = base
        self.fornecedor_id: int | None = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(*MARGENS)
        layout.setSpacing(20)
        self.titulo = texto("Novo fornecedor", "titulo")
        layout.addWidget(self.titulo)
        quadro = cartao()
        grade = QGridLayout(quadro)
        grade.setContentsMargins(24, 20, 24, 20)
        grade.setHorizontalSpacing(16)
        grade.setVerticalSpacing(12)
        self.tipo = CampoEscolha("Tipo", list(TIPOS_DE_PESSOA.items()))
        self.documento = Campo("CNPJ", "Formato: 00.000.000/0000-00")
        self.razao_social = Campo("Razão social")
        self.nome_fantasia = Campo("Nome fantasia", "Opcional.")
        self.telefone = Campo("Telefone", "Opcional.")
        self.email = Campo("E-mail", "Opcional.")
        self.endereco = Campo("Endereço", "Opcional.")
        self.observacoes = Campo("Observações", "Opcional.")
        posicoes = [
            (self.tipo, 0, 0, 1),
            (self.documento, 0, 1, 1),
            (self.razao_social, 1, 0, 1),
            (self.nome_fantasia, 1, 1, 1),
            (self.telefone, 2, 0, 1),
            (self.email, 2, 1, 1),
            (self.endereco, 3, 0, 2),
            (self.observacoes, 4, 0, 2),
        ]
        for campo, linha, coluna, largura in posicoes:
            grade.addWidget(campo, linha, coluna, 1, largura, Qt.AlignmentFlag.AlignTop)
        grade.setColumnStretch(0, 1)
        grade.setColumnStretch(1, 1)
        layout.addWidget(quadro)
        self.cancelar = botao("Cancelar")
        self.salvar = botao("Salvar", "principal")
        layout.addLayout(linha_de_acoes(self.cancelar, self.salvar))
        layout.addStretch()
        self.campos = {
            "tipo": self.tipo,
            "documento": self.documento,
            "razao_social": self.razao_social,
            "email": self.email,
        }
        self.tipo.caixa.currentIndexChanged.connect(lambda _: self._ajustar_ao_tipo())
        self.documento.caixa.editingFinished.connect(self._formatar_documento)
        formatar_ao_digitar(
            self.documento.caixa, lambda t: documento_ao_digitar(self.tipo.valor() or "pj", t)
        )
        formatar_ao_digitar(self.telefone.caixa, telefone_ao_digitar)
        self.cancelar.clicked.connect(self.cancelado.emit)
        self.salvar.clicked.connect(self._salvar)
        # Enter em qualquer campo salva, como nos diálogos (RNF05).
        for campo in (
            self.documento,
            self.razao_social,
            self.nome_fantasia,
            self.telefone,
            self.email,
            self.endereco,
            self.observacoes,
        ):
            campo.caixa.returnPressed.connect(self._salvar)

    def _ajustar_ao_tipo(self) -> None:
        pf = self.tipo.valor() == "pf"
        self.documento.rotulo.setText("CPF" if pf else "CNPJ")
        self.documento.definir_ajuda(
            "Formato: 000.000.000-00" if pf else "Formato: 00.000.000/0000-00"
        )
        self.razao_social.rotulo.setText("Nome" if pf else "Razão social")
        if self.documento.valor():
            self.documento.definir(documento_ao_digitar(self.tipo.valor(), self.documento.valor()))
        self.nome_fantasia.setVisible(not pf)

    def _formatar_documento(self) -> None:
        if self.tipo.valor():
            self.documento.definir(formatar_documento(self.tipo.valor(), self.documento.valor()))

    def abrir(self, fornecedor: Fornecedor | None) -> None:
        self.fornecedor_id = fornecedor.id if fornecedor else None
        self.titulo.setText("Editar fornecedor" if fornecedor else "Novo fornecedor")
        dados = fornecedor.dados() if fornecedor else DadosFornecedor("pj", "", "")
        self.tipo.definir(dados.tipo)
        self.documento.definir(formatar_documento(dados.tipo, dados.documento))
        self.razao_social.definir(dados.razao_social)
        self.nome_fantasia.definir(dados.nome_fantasia)
        self.telefone.definir(dados.telefone)
        self.email.definir(dados.email)
        self.endereco.definir(dados.endereco)
        self.observacoes.definir(dados.observacoes)
        for campo in self.campos.values():
            campo.limpar_erro()
        self._ajustar_ao_tipo()
        self.documento.caixa.setFocus()

    def dados(self) -> DadosFornecedor:
        return DadosFornecedor(
            self.tipo.valor(),
            self.documento.valor(),
            self.razao_social.valor(),
            self.nome_fantasia.valor(),
            self.telefone.valor(),
            self.email.valor(),
            self.endereco.valor(),
            self.observacoes.valor(),
        )

    def _salvar(self) -> None:
        dados = self.dados()
        erros = problemas_do_fornecedor(self.base.conexao, dados, ignorar_id=self.fornecedor_id)
        for chave, campo in self.campos.items():
            if chave in erros:
                campo.mostrar_erro(erros[chave])
            else:
                campo.limpar_erro()
        if erros:
            next(self.campos[c] for c in self.campos if c in erros).caixa.setFocus()
            return
        if self.fornecedor_id is None:
            self.fornecedor_id = cadastrar_fornecedor(self.base.conexao, dados)
        else:
            editar_fornecedor(self.base.conexao, self.fornecedor_id, dados)
        self.base.salvar()
        self.salvo.emit(self.fornecedor_id)
        confirmar_rapido(self, "Fornecedor salvo.")


# Diálogos de conta e chave ----------------------------------------------------------------


class DialogoItem(Dialogo):
    """Base dos diálogos de conta e de chave: confirma a repetição em outro fornecedor e
    oferece excluir (sem histórico) ou inativar e reativar (com histórico)."""

    TABELA = ""
    NOME = ""

    def __init__(self, pai, base: BaseDeDados, fornecedor: Fornecedor, titulo: str, item) -> None:
        super().__init__(pai, titulo, "Salvar")
        self.base = base
        self.fornecedor = fornecedor
        self.item = item
        self.item_id = item.id if item else None
        self.repeticao_confirmada = False
        self.aviso_repeticao = aviso("", "atencao")
        self.aviso_repeticao.setVisible(False)
        self.excluir: QPushButton | None = None
        self.ativar: QPushButton | None = None
        self.feito = ""

    def montar_acoes(self) -> None:
        self.corpo.addWidget(self.aviso_repeticao)
        linha = QHBoxLayout()
        linha.setSpacing(12)
        if self.item is not None:
            if item_tem_historico(self.base.conexao, self.TABELA, self.item.id):
                self.ativar = botao(
                    f"Inativar {self.NOME}" if self.item.ativa else f"Reativar {self.NOME}",
                    "perigo" if self.item.ativa else "secundario",
                )
                self.ativar.clicked.connect(self._trocar_ativa)
                linha.addWidget(self.ativar)
            else:
                self.excluir = botao(f"Excluir {self.NOME}", "perigo")
                self.excluir.clicked.connect(self._excluir)
                linha.addWidget(self.excluir)
        linha.addStretch()
        linha.addWidget(self.cancelar)
        linha.addWidget(self.confirmar)
        self.corpo.addLayout(linha)

    def outros(self) -> list[str]:
        return []

    def problemas(self) -> dict[str, str]:
        return {}

    def gravar(self) -> int:
        raise NotImplementedError

    def campos(self) -> dict:
        return {}

    def ao_confirmar(self) -> None:
        erros = self.problemas()
        for chave, campo in self.campos().items():
            if chave in erros:
                campo.mostrar_erro(erros[chave])
            else:
                campo.limpar_erro()
        if erros:
            next(c for k, c in self.campos().items() if k in erros).caixa.setFocus()
            return
        outros = self.outros()
        if outros and not self.repeticao_confirmada:
            mudar_aviso(
                self.aviso_repeticao,
                f"A mesma {self.NOME} já está cadastrada em {_lista_de_nomes(outros)}. Confira "
                "com o fornecedor antes de salvar.",
                "atencao",
            )
            self.aviso_repeticao.setVisible(True)
            self.confirmar.setText("Salvar mesmo assim")
            self.repeticao_confirmada = True
            return
        self.item_id = self.gravar()
        self.base.salvar()
        self.feito = f"{self.NOME.capitalize()} salva."
        self.accept()

    def _excluir(self) -> None:
        if perguntar(
            self,
            f"Excluir {self.NOME}",
            f"A {self.NOME} sai do cadastro deste fornecedor. Isso não pode ser desfeito.",
            "Excluir",
        ):
            excluir_item(self.base.conexao, self.TABELA, self.item.id)
            self.base.salvar()
            self.feito = f"{self.NOME.capitalize()} excluída."
            self.accept()

    def _trocar_ativa(self) -> None:
        if self.item.ativa and not perguntar(
            self,
            f"Inativar {self.NOME}",
            f"A {self.NOME} deixa de aparecer na Consulta. As marcações de cadastro ficam "
            "guardadas e voltam se ela for reativada.",
            "Inativar",
        ):
            return
        definir_item_ativo(self.base.conexao, self.TABELA, self.item.id, not self.item.ativa)
        self.base.salvar()
        estado = "reativada" if not self.item.ativa else "inativada"
        self.feito = f"{self.NOME.capitalize()} {estado}."
        self.accept()


class DialogoContaFornecedor(DialogoItem):
    """T14 · Conta bancária do fornecedor, sempre no documento dele (RN10)."""

    TABELA = "conta_fornecedor"
    NOME = "conta"

    def __init__(self, pai, base, fornecedor: Fornecedor, conta: ContaFornecedor | None):
        titulo = "Editar conta bancária" if conta else "Nova conta bancária"
        super().__init__(pai, base, fornecedor, titulo, conta)
        bancos = [(b.codigo, b.rotulo) for b in listar_bancos(base.conexao)]
        self.banco = CampoEscolha(
            "Banco", bancos, "Comece a digitar o código ou o nome.", busca=True
        )
        self.agencia = Campo("Agência")
        self.numero = Campo("Conta com dígito")
        self.tipo = CampoEscolha("Tipo", list(TIPOS_DE_CONTA.items()))
        self.corpo.addWidget(self.banco)
        linha = QHBoxLayout()
        linha.setSpacing(12)
        linha.addWidget(self.agencia)
        linha.addWidget(self.numero)
        self.corpo.addLayout(linha)
        self.corpo.addWidget(self.tipo)
        self.corpo.addWidget(
            texto(
                f"A conta precisa estar no {fornecedor.nome_do_documento} do próprio fornecedor "
                f"({fornecedor.documento_formatado}). Contas de terceiros não são aceitas.",
                "ajuda",
            )
        )
        if conta:
            self.banco.definir(conta.banco)
            self.agencia.definir(conta.agencia)
            self.numero.definir(conta.conta)
            self.tipo.definir(conta.tipo)
        else:
            self.banco.caixa.setCurrentIndex(-1)
        self.montar_acoes()

    def dados(self) -> DadosContaFornecedor:
        return DadosContaFornecedor(
            self.banco.valor(), self.agencia.valor(), self.numero.valor(), self.tipo.valor()
        )

    def campos(self) -> dict:
        return {"banco": self.banco, "agencia": self.agencia, "conta": self.numero}

    def problemas(self) -> dict[str, str]:
        return problemas_da_conta_fornecedor(
            self.base.conexao, self.fornecedor.id, self.dados(), self.item_id
        )

    def outros(self) -> list[str]:
        return outros_fornecedores_com_a_conta(self.base.conexao, self.fornecedor.id, self.dados())

    def gravar(self) -> int:
        return salvar_conta_fornecedor(
            self.base.conexao, self.fornecedor.id, self.dados(), self.item_id
        )


class DialogoChavePix(DialogoItem):
    """T15 · Chave Pix do fornecedor, conferida pelo formato do tipo (RN02)."""

    TABELA = "chave_pix"
    NOME = "chave"

    def __init__(self, pai, base, fornecedor: Fornecedor, chave: ChavePix | None):
        titulo = "Editar chave Pix" if chave else "Nova chave Pix"
        super().__init__(pai, base, fornecedor, titulo, chave)
        self.tipo = CampoEscolha("Tipo da chave", list(TIPOS_DE_CHAVE.items()))
        self.chave = Campo("Chave", "A chave é conferida pelo formato do tipo escolhido.")
        self.corpo.addWidget(self.tipo)
        self.corpo.addWidget(self.chave)
        if chave:
            self.tipo.definir(chave.tipo)
            self.chave.definir(chave.chave_formatada)
        else:
            self.tipo.caixa.setCurrentIndex(-1)
        self.tipo.caixa.currentIndexChanged.connect(lambda _: self._sugerir_documento())
        formatar_ao_digitar(self.chave.caixa, lambda t: chave_pix_ao_digitar(self.tipo.valor(), t))
        self.montar_acoes()

    def _sugerir_documento(self) -> None:
        """Chave de CNPJ ou CPF: o único valor aceito é o documento do fornecedor."""
        if self.tipo.valor() in ("cpf", "cnpj") and not self.chave.valor().strip():
            self.chave.definir(self.fornecedor.documento_formatado)

    def campos(self) -> dict:
        return {"tipo": self.tipo, "chave": self.chave}

    def problemas(self) -> dict[str, str]:
        if not self.tipo.valor():
            return {"tipo": "Escolha o tipo da chave."}
        problema = problema_da_chave(
            self.base.conexao, self.fornecedor, self.tipo.valor(), self.chave.valor(), self.item_id
        )
        return {"chave": problema} if problema else {}

    def outros(self) -> list[str]:
        return outros_fornecedores_com_a_chave(
            self.base.conexao, self.fornecedor.id, self.tipo.valor(), self.chave.valor()
        )

    def gravar(self) -> int:
        return salvar_chave_pix(
            self.base.conexao,
            self.fornecedor.id,
            self.tipo.valor(),
            self.chave.valor(),
            self.item_id,
        )


# Ficha ------------------------------------------------------------------------------------


class FichaFornecedor(QWidget):
    """T12 e T13 · Ficha com as abas Dados, Contas e Pix, e Cadastros."""

    voltar_lista = Signal()
    editar_pedido = Signal(object)
    excluido = Signal()

    def __init__(self, base: BaseDeDados) -> None:
        super().__init__()
        self.base = base
        self.fornecedor: Fornecedor | None = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(*MARGENS)
        layout.setSpacing(12)
        self.voltar = botao("← Fornecedores", "link")
        layout.addLayout(linha_de_acoes(self.voltar, alinhar="esquerda"))
        topo = QHBoxLayout()
        nomes = QVBoxLayout()
        nomes.setSpacing(4)
        self.titulo = texto("", "titulo")
        linha_doc = QHBoxLayout()
        linha_doc.setSpacing(8)
        self.documento = texto("", "apoio")
        self.situacao = etiqueta("")
        linha_doc.addWidget(self.documento)
        linha_doc.addWidget(self.situacao)
        linha_doc.addStretch()
        nomes.addWidget(self.titulo)
        nomes.addLayout(linha_doc)
        topo.addLayout(nomes, 1)
        self.editar = botao("Editar")
        self.imprimir = botao("Imprimir ficha")
        self.ativar = botao("Inativar", "perigo")
        self.excluir = botao("Excluir", "perigo")
        for b in (self.editar, self.imprimir, self.ativar, self.excluir):
            topo.addWidget(b, 0, Qt.AlignmentFlag.AlignTop)
        layout.addLayout(topo)

        self.abas = Abas()
        layout.addWidget(self.abas, 1)
        self.aba_dados = QWidget()
        coluna = QVBoxLayout(self.aba_dados)
        coluna.setContentsMargins(0, 16, 0, 0)
        self.quadro_dados = cartao()
        self.grade_dados = QGridLayout(self.quadro_dados)
        self.grade_dados.setContentsMargins(24, 16, 24, 16)
        self.grade_dados.setHorizontalSpacing(32)
        self.grade_dados.setVerticalSpacing(10)
        self.grade_dados.setColumnStretch(1, 1)
        coluna.addWidget(self.quadro_dados)
        coluna.addStretch()
        self.abas.addTab(self.aba_dados, "Dados")

        self.aba_contas = QWidget()
        coluna = QVBoxLayout(self.aba_contas)
        coluna.setContentsMargins(0, 16, 0, 0)
        coluna.setSpacing(12)
        self.nova_conta = botao("Nova conta")
        coluna.addLayout(self._cabecalho_secao("Contas bancárias", self.nova_conta))
        self.sem_contas = texto("Nenhuma conta bancária cadastrada.", "apoio")
        coluna.addWidget(self.sem_contas)
        self.tabela_contas = Tabela(["Banco", "Agência", "Conta", "Tipo", "Situação"])
        coluna.addWidget(self.tabela_contas)
        self.nova_chave = botao("Nova chave Pix")
        coluna.addLayout(self._cabecalho_secao("Chaves Pix", self.nova_chave))
        self.sem_chaves = texto("Nenhuma chave Pix cadastrada.", "apoio")
        coluna.addWidget(self.sem_chaves)
        self.tabela_chaves = Tabela(["Tipo", "Chave", "Situação"])
        coluna.addWidget(self.tabela_chaves)
        coluna.addWidget(
            texto(
                "Clique numa conta ou chave, ou use Enter, para editar, excluir ou inativar.",
                "ajuda",
            )
        )
        coluna.addStretch()
        for tabela, larga in ((self.tabela_contas, 0), (self.tabela_chaves, 1)):
            tabela.setWordWrap(False)
            cabecalho = tabela.horizontalHeader()
            cabecalho.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
            cabecalho.setSectionResizeMode(larga, QHeaderView.ResizeMode.Stretch)
        self.abas.addTab(self.aba_contas, "Contas e Pix")

        self.aba_cadastros = PainelCadastros(base)
        self.abas.addTab(self.aba_cadastros, "Cadastros")
        # Com a primeira marcação, o fornecedor passa a ter histórico e só pode ser inativado.
        self.aba_cadastros.alterado.connect(self._atualizar_excluir)

        self.voltar.clicked.connect(self.voltar_lista.emit)
        self.editar.clicked.connect(lambda: self.editar_pedido.emit(self.fornecedor))
        self.imprimir.clicked.connect(self.imprimir_ficha)
        self.ativar.clicked.connect(self._trocar_ativo)
        self.excluir.clicked.connect(self._excluir)
        self.nova_conta.clicked.connect(lambda: self.abrir_conta(None))
        self.nova_chave.clicked.connect(lambda: self.abrir_chave(None))
        self.tabela_contas.escolhida.connect(
            lambda linha: self.abrir_conta(self.tabela_contas.dado_da_linha(linha))
        )
        self.tabela_chaves.escolhida.connect(
            lambda linha: self.abrir_chave(self.tabela_chaves.dado_da_linha(linha))
        )

    def _atualizar_excluir(self) -> None:
        self.excluir.setVisible(not tem_historico(self.base.conexao, self.fornecedor.id))

    @staticmethod
    def _cabecalho_secao(titulo: str, acao: QPushButton) -> QHBoxLayout:
        linha = QHBoxLayout()
        linha.addWidget(texto(titulo, "secao"), 1)
        linha.addWidget(acao)
        return linha

    def mostrar(self, fornecedor_id: int) -> None:
        f = obter_fornecedor(self.base.conexao, fornecedor_id)
        self.fornecedor = f
        self.titulo.setText(f.razao_social)
        self.documento.setText(f"{f.nome_do_documento} {f.documento_formatado}")
        self.situacao.setText("✓ Ativo" if f.ativo else "Inativo")
        self.ativar.setText("Inativar" if f.ativo else "Reativar")
        self.ativar.setProperty("tipo", "perigo" if f.ativo else "secundario")
        self.ativar.style().polish(self.ativar)
        self._atualizar_excluir()
        self._mostrar_dados(f)
        self._mostrar_contas_e_chaves(f)
        self.aba_cadastros.mostrar(f)

    def _mostrar_dados(self, f: Fornecedor) -> None:
        while self.grade_dados.count():
            self.grade_dados.takeAt(0).widget().deleteLater()
        contato = " · ".join(v for v in (f.telefone, f.email) if v)
        linhas = [("Tipo", f.nome_do_tipo)]
        if f.tipo == "pj":
            linhas.append(("Nome fantasia", f.nome_fantasia or "—"))
        linhas += [
            ("Contato", contato or "—"),
            ("Endereço", f.endereco or "—"),
            ("Observações", f.observacoes or "—"),
            (
                "Cadastro",
                f"Criado em {_data(f.criado_em)} · última alteração em {_data(f.alterado_em)}",
            ),
        ]
        for numero, (rotulo, valor) in enumerate(linhas):
            self.grade_dados.addWidget(
                texto(rotulo, "rotulo"), numero, 0, Qt.AlignmentFlag.AlignTop
            )
            campo = texto(valor)
            campo.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            self.grade_dados.addWidget(campo, numero, 1)

    def _mostrar_contas_e_chaves(self, f: Fornecedor) -> None:
        contas = listar_contas_fornecedor(self.base.conexao, f.id)
        self.sem_contas.setVisible(not contas)
        self.tabela_contas.setVisible(bool(contas))
        self.tabela_contas.setRowCount(len(contas))
        for linha, c in enumerate(contas):
            self.tabela_contas.celula(linha, 0, c.banco_rotulo, c)
            self.tabela_contas.celula(linha, 1, c.agencia)
            self.tabela_contas.celula(linha, 2, c.conta)
            self.tabela_contas.celula(linha, 3, c.nome_do_tipo)
            self.tabela_contas.celula(linha, 4, "")
            self.tabela_contas.setCellWidget(linha, 4, _situacao(c.ativa, feminino=True))
        chaves = listar_chaves(self.base.conexao, f.id)
        self.sem_chaves.setVisible(not chaves)
        self.tabela_chaves.setVisible(bool(chaves))
        self.tabela_chaves.setRowCount(len(chaves))
        for linha, ch in enumerate(chaves):
            self.tabela_chaves.celula(linha, 0, ch.nome_do_tipo, ch)
            self.tabela_chaves.celula(linha, 1, ch.chave_formatada)
            self.tabela_chaves.celula(linha, 2, "")
            self.tabela_chaves.setCellWidget(linha, 2, _situacao(ch.ativa, feminino=True))
        for tabela in (self.tabela_contas, self.tabela_chaves):
            tabela.ajustar()
            altura = tabela.horizontalHeader().height() + sum(
                tabela.rowHeight(i) for i in range(tabela.rowCount())
            )
            tabela.setFixedHeight(altura + 4)

    def criar_dialogo_conta(self, conta: ContaFornecedor | None) -> DialogoContaFornecedor:
        return DialogoContaFornecedor(self, self.base, self.fornecedor, conta)

    def criar_dialogo_chave(self, chave: ChavePix | None) -> DialogoChavePix:
        return DialogoChavePix(self, self.base, self.fornecedor, chave)

    def abrir_conta(self, conta: ContaFornecedor | None) -> None:
        self._depois_do_dialogo(self.criar_dialogo_conta(conta))

    def abrir_chave(self, chave: ChavePix | None) -> None:
        self._depois_do_dialogo(self.criar_dialogo_chave(chave))

    def _depois_do_dialogo(self, dialogo: DialogoItem) -> None:
        if dialogo.exec():
            self.mostrar(self.fornecedor.id)
            confirmar_rapido(self, dialogo.feito)

    def imprimir_ficha(self) -> None:
        """RF14 · Ficha completa em A4, com pré-visualização e opção de salvar em PDF."""
        f = self.fornecedor
        abrir_janela_impressao(
            self,
            ficha_completa(
                f,
                listar_contas_fornecedor(self.base.conexao, f.id),
                listar_chaves(self.base.conexao, f.id),
                obter_entidade(self.base.conexao),
            ),
        )

    def _trocar_ativo(self) -> None:
        f = self.fornecedor
        if f.ativo and not perguntar(
            self,
            "Inativar este fornecedor?",
            "Ele deixa de aparecer na Consulta. As marcações de cadastro ficam guardadas e "
            "voltam se ele for reativado.",
            "Inativar",
        ):
            return
        definir_fornecedor_ativo(self.base.conexao, f.id, not f.ativo)
        self.base.salvar()
        self.mostrar(f.id)
        confirmar_rapido(self, "Fornecedor reativado." if not f.ativo else "Fornecedor inativado.")

    def _excluir(self) -> None:
        f = self.fornecedor
        if perguntar(
            self,
            "Excluir este fornecedor?",
            f"{f.razao_social}, com as contas e chaves Pix dele, sai do cadastro. Isso não pode "
            "ser desfeito. Só é possível porque ele ainda não tem histórico de cadastros.",
            "Excluir",
        ):
            excluir_fornecedor(self.base.conexao, f.id)
            self.base.salvar()
            self.excluido.emit()
            confirmar_rapido(self, "Fornecedor excluído.")


# Página -----------------------------------------------------------------------------------


class PaginaFornecedores(QStackedWidget):
    def __init__(self, base: BaseDeDados) -> None:
        super().__init__()
        self.base = base
        self.lista = ListaFornecedores()
        self.formulario = FormularioFornecedor(base)
        self.ficha = FichaFornecedor(base)
        for pagina in (self.lista, self.formulario, self.ficha):
            self.addWidget(pagina)
        self.lista.busca.textChanged.connect(lambda _: self.atualizar())
        self.lista.inativos.toggled.connect(lambda _: self.atualizar())
        self.lista.novo.clicked.connect(lambda: self.abrir_formulario(None))
        self.lista.tabela.escolhida.connect(
            lambda linha: self.abrir_ficha(self.lista.tabela.dado_da_linha(linha))
        )
        self.formulario.salvo.connect(self.abrir_ficha)
        self.formulario.cancelado.connect(self._cancelar_formulario)
        self.ficha.voltar_lista.connect(self.voltar_para_lista)
        self.ficha.editar_pedido.connect(self.abrir_formulario)
        self.ficha.excluido.connect(self.voltar_para_lista)
        self.atualizar()

    def atualizar(self) -> None:
        busca = self.lista.busca.text()
        self.lista.mostrar(
            listar_fornecedores(self.base.conexao, busca, self.lista.inativos.isChecked()),
            buscando=bool(busca.strip()),
        )

    def abrir_formulario(self, fornecedor: Fornecedor | None) -> None:
        self.formulario.abrir(fornecedor)
        self.setCurrentWidget(self.formulario)

    def _cancelar_formulario(self) -> None:
        if self.formulario.fornecedor_id is not None:
            self.abrir_ficha(self.formulario.fornecedor_id)
        else:
            self.voltar_para_lista()

    def abrir_ficha(self, fornecedor_id: int) -> None:
        self.ficha.mostrar(fornecedor_id)
        self.ficha.abas.setCurrentIndex(0)
        self.setCurrentWidget(self.ficha)

    def voltar_para_lista(self) -> None:
        self.atualizar()
        self.setCurrentWidget(self.lista)
        self.lista.busca.setFocus()
