"""Telas de acesso: criar senha (T01), chave de recuperação (T02), entrada (T04) e
nova senha com a chave (T05)."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QCheckBox, QFileDialog, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from baliza.dados.banco import BaseDeDados
from baliza.dados.cofre import ChaveIncorreta, ErroDeArquivo, SenhaIncorreta
from baliza.dominio.senha import mensagem_senha_fraca, problemas_da_senha
from baliza.interface import impressao
from baliza.interface.componentes import (
    Campo,
    aviso,
    botao,
    cartao,
    linha_de_acoes,
    mudar_aviso,
    texto,
)
from baliza.interface.tema import CORES

LARGURA_CARTAO = 520


class TelaCentral(QWidget):
    """Fundo da janela com um cartão centralizado e a marca do Baliza no topo."""

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("fundo")
        externo = QVBoxLayout(self)
        externo.addStretch()
        linha = QHBoxLayout()
        linha.addStretch()
        self.cartao = cartao()
        self.cartao.setFixedWidth(LARGURA_CARTAO)
        linha.addWidget(self.cartao)
        linha.addStretch()
        externo.addLayout(linha)
        externo.addStretch()
        self.corpo = QVBoxLayout(self.cartao)
        self.corpo.setContentsMargins(40, 36, 40, 36)
        self.corpo.setSpacing(16)
        marca = texto(f'<span style="color: {CORES["accent/default"]};">▍</span>Baliza', "marca")
        self.corpo.addWidget(marca)

    def adicionar(self, widget) -> None:
        if isinstance(widget, QWidget):
            self.corpo.addWidget(widget)
        else:
            self.corpo.addLayout(widget)


def _validar_nova_senha(campo_senha: Campo, campo_confirma: Campo) -> str | None:
    senha = campo_senha.valor()
    faltando = problemas_da_senha(senha)
    if faltando:
        campo_senha.mostrar_erro(mensagem_senha_fraca(faltando))
        campo_senha.caixa.setFocus()
        return None
    if campo_confirma.valor() != senha:
        campo_confirma.mostrar_erro("As senhas não conferem. Digite a mesma senha nos dois campos.")
        campo_confirma.caixa.setFocus()
        return None
    return senha


class TelaCriarSenha(TelaCentral):
    """T01 · Boas-vindas e criação da senha."""

    senha_criada = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.adicionar(texto("Bem-vindo ao Baliza", "titulo"))
        self.adicionar(
            texto(
                "Crie a senha que protege os dados. Ela será pedida toda vez que o sistema abrir.",
                "apoio",
            )
        )
        self.senha = Campo("Senha", "Mínimo de 10 caracteres, com letras e números.", senha=True)
        self.confirma = Campo("Confirme a senha", senha=True)
        self.criar = botao("Criar senha", "principal")
        for item in (self.senha, self.confirma, linha_de_acoes(self.criar)):
            self.adicionar(item)
        self.criar.clicked.connect(self._criar)
        self.confirma.caixa.returnPressed.connect(self._criar)
        self.senha.caixa.returnPressed.connect(self.confirma.caixa.setFocus)

    def _criar(self) -> None:
        senha = _validar_nova_senha(self.senha, self.confirma)
        if senha:
            self.senha_criada.emit(senha)


class TelaChaveRecuperacao(TelaCentral):
    """T02 · Mostra a chave uma única vez e oferece imprimir ou salvar em PDF."""

    continuar = Signal()

    def __init__(self, chave: str, nome_entidade: str | None = None, logo: bytes | None = None):
        super().__init__()
        self.chave = chave
        self._html = impressao.html_chave_recuperacao(
            chave, datetime.now(), nome_entidade, com_logo=bool(logo)
        )
        self._logo = logo
        self.adicionar(texto("Guarde sua chave de recuperação", "titulo"))
        self.adicionar(
            texto(
                "Se esquecer a senha, só esta chave permite entrar de novo. "
                "Ela aparece uma única vez.",
                "apoio",
            )
        )
        rotulo_chave = QLabel(chave)
        rotulo_chave.setObjectName("chave")
        rotulo_chave.setAlignment(Qt.AlignmentFlag.AlignCenter)
        rotulo_chave.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.adicionar(rotulo_chave)
        self.imprimir = botao("Imprimir")
        self.salvar_pdf = botao("Salvar em PDF")
        self.adicionar(linha_de_acoes(self.imprimir, self.salvar_pdf, alinhar="esquerda"))
        self.retorno = aviso("", "sucesso")
        self.retorno.setVisible(False)
        self.adicionar(self.retorno)
        self.guardei = QCheckBox("Guardei a chave em lugar seguro")
        self.adicionar(self.guardei)
        self.botao_continuar = botao("Continuar", "principal")
        self.botao_continuar.setEnabled(False)
        self.adicionar(linha_de_acoes(self.botao_continuar))
        self.guardei.toggled.connect(self.botao_continuar.setEnabled)
        self.botao_continuar.clicked.connect(self.continuar.emit)
        self.imprimir.clicked.connect(self._imprimir)
        self.salvar_pdf.clicked.connect(self._escolher_pdf)

    def _imprimir(self) -> None:
        if impressao.imprimir(self._html, self, self._logo):
            mudar_aviso(self.retorno, "Chave enviada para a impressora.", "sucesso")
            self.retorno.setVisible(True)

    def _escolher_pdf(self) -> None:
        caminho, _ = QFileDialog.getSaveFileName(
            self,
            "Salvar a chave em PDF",
            str(Path.home() / "baliza-chave-de-recuperacao.pdf"),
            "PDF (*.pdf)",
        )
        if caminho:
            self.gravar_pdf(caminho)

    def gravar_pdf(self, caminho: str) -> None:
        impressao.salvar_pdf(self._html, caminho, self._logo)
        mudar_aviso(self.retorno, f"Chave salva em {caminho}.", "sucesso")
        self.retorno.setVisible(True)


class TelaEntrada(TelaCentral):
    """T04 · Pede a senha toda vez que o Baliza abre."""

    entrou = Signal(object)
    esqueci = Signal()

    def __init__(self, caminho: Path, nome_entidade: str | None = None) -> None:
        super().__init__()
        self.caminho = caminho
        self.adicionar(texto(nome_entidade or "Baliza", "titulo"))
        self.adicionar(texto("Digite a senha para abrir os dados.", "apoio"))
        self.erro = aviso("Senha incorreta. Confira e tente de novo.", "erro")
        self.erro.setVisible(False)
        self.adicionar(self.erro)
        self.senha = Campo("Senha", senha=True)
        self.adicionar(self.senha)
        self.link_esqueci = botao("Esqueci a senha", "link")
        self.entrar = botao("Entrar", "principal")
        linha = QHBoxLayout()
        linha.addWidget(self.link_esqueci)
        linha.addStretch()
        linha.addWidget(self.entrar)
        self.adicionar(linha)
        self.entrar.clicked.connect(self._entrar)
        self.senha.caixa.returnPressed.connect(self._entrar)
        self.link_esqueci.clicked.connect(self.esqueci.emit)
        self.senha.caixa.setFocus()

    def _entrar(self) -> None:
        try:
            base = BaseDeDados.abrir(self.caminho, senha=self.senha.valor())
        except SenhaIncorreta as erro:
            self.senha.mostrar_erro("Senha incorreta.")
            mudar_aviso(self.erro, str(erro), "erro")
            self.erro.setVisible(True)
            self.senha.caixa.selectAll()
            self.senha.caixa.setFocus()
            return
        except ErroDeArquivo as erro:
            mudar_aviso(self.erro, str(erro), "erro")
            self.erro.setVisible(True)
            return
        self.entrou.emit(base)


class TelaNovaSenha(TelaCentral):
    """T05 · Cria uma senha nova com a chave de recuperação."""

    senha_trocada = Signal(object)
    voltar = Signal()

    def __init__(self, caminho: Path) -> None:
        super().__init__()
        self.caminho = caminho
        self.adicionar(texto("Criar uma senha nova", "titulo"))
        self.adicionar(
            texto(
                "Digite a chave de recuperação e crie uma senha nova. "
                "Os dados continuam os mesmos.",
                "apoio",
            )
        )
        self.chave = Campo("Chave de recuperação", "Como está na folha impressa ou no PDF.")
        self.senha = Campo("Nova senha", "Mínimo de 10 caracteres, com letras e números.", True)
        self.confirma = Campo("Confirme a nova senha", senha=True)
        self.botao_voltar = botao("Voltar")
        self.criar = botao("Criar senha nova", "principal")
        for item in (
            self.chave,
            self.senha,
            self.confirma,
            linha_de_acoes(self.botao_voltar, self.criar),
        ):
            self.adicionar(item)
        self.criar.clicked.connect(self._criar)
        self.botao_voltar.clicked.connect(self.voltar.emit)

    def _criar(self) -> None:
        senha = _validar_nova_senha(self.senha, self.confirma)
        if not senha:
            return
        try:
            base = BaseDeDados.abrir(self.caminho, chave=self.chave.valor())
        except ChaveIncorreta:
            self.chave.mostrar_erro("Chave inválida. Confira as letras e os números.")
            self.chave.caixa.setFocus()
            return
        base.cofre.trocar_senha(senha)
        self.senha_trocada.emit(base)
