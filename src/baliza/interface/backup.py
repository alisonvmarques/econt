"""Configurações · Backup (T23): automático ao fechar, exportar e restaurar (RF22 a RF25)."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from baliza.dados.backup import (
    BACKUP_AUTOMATICO,
    COPIAS,
    COPIAS_MAXIMO,
    automatico_ligado,
    copias_escolhidas,
    exportar,
    listar_backups,
    manter_ultimas,
    pasta_de_backups,
    restaurar,
)
from baliza.dados.banco import BaseDeDados
from baliza.dados.cofre import ErroDeArquivo
from baliza.interface.componentes import (
    Campo,
    Dialogo,
    Tabela,
    aviso,
    botao,
    cartao,
    confirmar_rapido,
    linha_de_acoes,
    mudar_aviso,
    texto,
)


def _quando(momento: datetime) -> str:
    return momento.strftime("%d/%m/%Y às %H:%M")


class DialogoRestaurar(Dialogo):
    """Confirma a troca dos dados e pede a senha ou a chave de recuperação do backup."""

    def __init__(self, pai: QWidget | None, arquivo: Path, caminho_dados: Path) -> None:
        super().__init__(pai, "Restaurar backup", "Substituir os dados atuais")
        self.arquivo = Path(arquivo)
        self.caminho_dados = Path(caminho_dados)
        self.base_restaurada: BaseDeDados | None = None
        self.confirmar.setProperty("tipo", "perigo")
        self.corpo.addWidget(
            texto(
                f"Os dados atuais serão substituídos pelos do arquivo {self.arquivo.name}. "
                "Antes, eles são guardados como um backup, para nada se perder.",
                "apoio",
            )
        )
        self.segredo = Campo(
            "Senha do backup", "A senha que valia quando o backup foi feito.", senha=True
        )
        self.usar_chave = QCheckBox("Usar a chave de recuperação em vez da senha")
        self.corpo.addWidget(self.segredo)
        self.corpo.addWidget(self.usar_chave)
        self.usar_chave.toggled.connect(self._trocar_segredo)
        self.fechar_corpo()

    def _trocar_segredo(self, chave: bool) -> None:
        self.segredo.rotulo.setText(
            "Chave de recuperação do backup" if chave else "Senha do backup"
        )
        self.segredo.caixa.setEchoMode(
            self.segredo.caixa.EchoMode.Normal if chave else self.segredo.caixa.EchoMode.Password
        )
        self.segredo.definir_ajuda(
            "Formato: XXXX-XXXX-XXXX-XXXX-XXXX-XXXX."
            if chave
            else "A senha que valia quando o backup foi feito."
        )
        self.segredo.limpar_erro()

    def ao_confirmar(self) -> None:
        valor = self.segredo.valor()
        if not valor.strip():
            self.segredo.mostrar_erro(
                "Informe a chave de recuperação."
                if self.usar_chave.isChecked()
                else "Informe a senha."
            )
            return
        credencial = {"chave": valor} if self.usar_chave.isChecked() else {"senha": valor}
        try:
            self.base_restaurada = restaurar(self.arquivo, self.caminho_dados, **credencial)
        except ErroDeArquivo as erro:
            self.segredo.mostrar_erro(str(erro))
            self.segredo.caixa.setFocus()
            return
        self.accept()


class PaginaBackup(QWidget):
    restaurado = Signal(object)

    def __init__(self, base: BaseDeDados) -> None:
        super().__init__()
        self.base = base
        self.caminho = Path(base.cofre.caminho)
        self.pasta = pasta_de_backups(self.caminho)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 20, 0, 0)
        layout.setSpacing(16)
        quadro = cartao()
        interno = QVBoxLayout(quadro)
        interno.setContentsMargins(24, 20, 24, 20)
        interno.setSpacing(10)
        interno.addWidget(texto("Backup automático", "secao"))
        self.automatico = QCheckBox("Fazer backup toda vez que o Baliza for fechado")
        interno.addWidget(self.automatico)
        linha = QHBoxLayout()
        linha.setSpacing(16)
        coluna = QVBoxLayout()
        coluna.setSpacing(6)
        rotulo = texto("Quantas cópias guardar", "rotulo")
        self.copias = QSpinBox()
        self.copias.setRange(1, COPIAS_MAXIMO)
        self.copias.setAccessibleName("Quantas cópias guardar")
        rotulo.setBuddy(self.copias)
        coluna.addWidget(rotulo)
        coluna.addWidget(self.copias)
        linha.addLayout(coluna)
        linha.addWidget(
            texto(
                "A mais antiga é apagada a cada cópia nova. Os backups são criptografados como o "
                f"arquivo original e ficam em {self.pasta}.",
                "ajuda",
            ),
            1,
        )
        interno.addLayout(linha)
        layout.addWidget(quadro)
        self.vazia = texto(
            "Nenhum backup ainda. O primeiro é feito quando o Baliza for fechado.", "apoio"
        )
        layout.addWidget(self.vazia)
        self.tabela = Tabela(["Últimos backups", "Tamanho"])
        self.tabela.setSelectionMode(Tabela.SelectionMode.NoSelection)
        self.tabela.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.tabela)
        self.exportar = botao("Exportar backup…")
        self.restaurar = botao("Restaurar backup…")
        layout.addLayout(linha_de_acoes(self.exportar, self.restaurar, alinhar="esquerda"))
        self.retorno = aviso("", "sucesso")
        self.retorno.setVisible(False)
        layout.addWidget(self.retorno)
        layout.addStretch()

        self.automatico.setChecked(automatico_ligado(base))
        self.copias.setValue(copias_escolhidas(base))
        self.automatico.toggled.connect(self._trocar_automatico)
        self.copias.valueChanged.connect(self._trocar_copias)
        self.exportar.clicked.connect(self._exportar)
        self.restaurar.clicked.connect(self._restaurar)
        self.atualizar()

    def showEvent(self, evento) -> None:  # noqa: N802 (nome do Qt)
        self.atualizar()
        super().showEvent(evento)

    def atualizar(self) -> None:
        backups = listar_backups(self.pasta)
        self.vazia.setVisible(not backups)
        self.tabela.setVisible(bool(backups))
        self.tabela.setRowCount(len(backups))
        for linha, b in enumerate(backups):
            self.tabela.celula(linha, 0, _quando(b.quando), str(b.caminho))
            self.tabela.celula(linha, 1, b.tamanho_legivel)
        self.tabela.ajustar()
        altura = self.tabela.horizontalHeader().height() + sum(
            self.tabela.rowHeight(i) for i in range(len(backups))
        )
        self.tabela.setFixedHeight(min(altura + 4, 360))

    def _trocar_automatico(self, ligado: bool) -> None:
        self.base.definir_configuracao(BACKUP_AUTOMATICO, "sim" if ligado else "nao")
        self.base.salvar()
        self.copias.setEnabled(ligado)
        confirmar_rapido(
            self, "Backup automático ligado." if ligado else "Backup automático desligado."
        )

    def _trocar_copias(self, quantas: int) -> None:
        self.base.definir_configuracao(COPIAS, str(quantas))
        self.base.salvar()
        apagados = manter_ultimas(self.pasta, quantas)
        self.atualizar()
        if apagados:
            confirmar_rapido(self, f"Guardando {quantas} cópias. As mais antigas foram apagadas.")

    # Escolhas de arquivo ficam em métodos próprios para os testes trocarem.
    def escolher_pasta(self) -> str:
        return QFileDialog.getExistingDirectory(self, "Exportar backup para", str(Path.home()))

    def escolher_arquivo(self) -> str:
        caminho, _ = QFileDialog.getOpenFileName(
            self, "Restaurar backup", str(self.pasta), "Backup do Baliza (*.baliza)"
        )
        return caminho

    def criar_dialogo_restaurar(self, arquivo: Path) -> DialogoRestaurar:
        return DialogoRestaurar(self, arquivo, self.caminho)

    def _exportar(self) -> None:
        pasta = self.escolher_pasta()
        if not pasta:
            return
        self.base.salvar()
        try:
            feito = exportar(self.caminho, Path(pasta))
        except OSError as erro:
            mudar_aviso(
                self.retorno,
                f"Não foi possível exportar para {pasta}: {erro.strerror or erro}. Confira se o "
                "pendrive ou o disco está conectado e com espaço.",
                "erro",
            )
        else:
            mudar_aviso(
                self.retorno,
                f"Backup exportado para {feito.parent} em {_quando(datetime.now())}. "
                f"Arquivo: {feito.name}.",
                "sucesso",
            )
        self.retorno.setVisible(True)

    def _restaurar(self) -> None:
        arquivo = self.escolher_arquivo()
        if not arquivo:
            return
        self.base.salvar()
        dialogo = self.criar_dialogo_restaurar(Path(arquivo))
        if dialogo.exec() and dialogo.base_restaurada is not None:
            self.restaurado.emit(dialogo.base_restaurada)
