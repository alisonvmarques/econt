"""Janela principal do Baliza: conduz o acesso e depois mostra as áreas do sistema."""

from __future__ import annotations

from contextlib import suppress
from pathlib import Path

from PySide6.QtWidgets import QApplication, QMainWindow, QStackedWidget, QWidget

from baliza.dados.backup import backup_ao_fechar
from baliza.dados.banco import BaseDeDados
from baliza.dados.entidade import Entidade, obter_entidade, salvar_entidade
from baliza.dados.local import caminho_padrao
from baliza.interface.acesso import (
    TelaChaveRecuperacao,
    TelaCriarSenha,
    TelaEntrada,
    TelaNovaSenha,
)
from baliza.interface.area_principal import AreaPrincipal
from baliza.interface.componentes import confirmar_rapido
from baliza.interface.entidade import TelaDadosEntidade
from baliza.interface.tema import folha_de_estilo

TITULO = "Baliza"
CHAVE_GUARDADA = "chave_de_recuperacao_guardada"
LARGURA_INICIAL, ALTURA_INICIAL = 1280, 800
LARGURA_MINIMA, ALTURA_MINIMA = 1024, 640


class JanelaPrincipal(QMainWindow):
    def __init__(self, caminho: str | Path | None = None) -> None:
        super().__init__()
        self.caminho = Path(caminho) if caminho else caminho_padrao()
        self.base: BaseDeDados | None = None
        self.setWindowTitle(TITULO)
        self.resize(LARGURA_INICIAL, ALTURA_INICIAL)
        self.setMinimumSize(LARGURA_MINIMA, ALTURA_MINIMA)
        # No nível da aplicação, o tema vale também para diálogos e peças criadas antes de
        # entrar na janela.
        QApplication.instance().setStyleSheet(folha_de_estilo())
        self.pilha = QStackedWidget()
        self.setCentralWidget(self.pilha)
        if self.caminho.exists():
            self.mostrar_entrada()
        else:
            self._mostrar(TelaCriarSenha()).senha_criada.connect(self._criar_dados)

    # --- navegação entre telas de acesso
    def _mostrar(self, tela: QWidget) -> QWidget:
        anterior = self.pilha.currentWidget()
        self.pilha.addWidget(tela)
        self.pilha.setCurrentWidget(tela)
        if anterior is not None:
            self.pilha.removeWidget(anterior)
            anterior.deleteLater()
        return tela

    def tela_atual(self) -> QWidget:
        return self.pilha.currentWidget()

    def mostrar_entrada(self) -> None:
        tela = self._mostrar(TelaEntrada(self.caminho))
        tela.entrou.connect(self._acesso_liberado)
        tela.esqueci.connect(self._mostrar_nova_senha)

    def _mostrar_nova_senha(self) -> None:
        tela = self._mostrar(TelaNovaSenha(self.caminho))
        tela.senha_trocada.connect(self._acesso_liberado)
        tela.voltar.connect(self.mostrar_entrada)

    def _criar_dados(self, senha: str) -> None:
        self.caminho.parent.mkdir(parents=True, exist_ok=True)
        self.base, chave = BaseDeDados.criar(self.caminho, senha)
        self._mostrar_chave(chave)

    def _mostrar_chave(self, chave: str) -> None:
        self._mostrar(TelaChaveRecuperacao(chave)).continuar.connect(self._chave_guardada)

    def _chave_guardada(self) -> None:
        self.base.definir_configuracao(CHAVE_GUARDADA, "sim")
        self.base.salvar()
        self._seguir()

    def _acesso_liberado(self, base: BaseDeDados) -> None:
        self.base = base
        self._seguir()

    def _seguir(self) -> None:
        """Ordem do primeiro uso: chave de recuperação guardada (RF20), depois a entidade (RF15).

        Se o sistema foi fechado antes da confirmação de que a chave foi guardada, a chave
        mostrada pode ter se perdido: gera uma nova (a anterior deixa de valer) e mostra de novo.
        """
        if self.base.configuracao(CHAVE_GUARDADA) != "sim":
            self._mostrar_chave(self.base.cofre.gerar_nova_chave())
            return
        if obter_entidade(self.base.conexao) is None:
            self._mostrar(TelaDadosEntidade()).salva.connect(self._salvar_entidade)
        else:
            self.area = self._mostrar(AreaPrincipal(self.base))
            self.area.restaurado.connect(self._trocar_pelos_restaurados)

    def _trocar_pelos_restaurados(self, restaurada: BaseDeDados) -> None:
        """Depois de restaurar, os dados antigos em memória são descartados sem gravar: o
        arquivo já tem os dados do backup (e os antigos viraram um backup)."""
        self.base.conexao.close()
        self.base = restaurada
        self._seguir()
        confirmar_rapido(self, "Backup restaurado.")

    def _salvar_entidade(self, entidade: Entidade) -> None:
        salvar_entidade(self.base.conexao, entidade)
        self.base.salvar()
        self._seguir()

    def closeEvent(self, evento) -> None:  # noqa: N802 (nome do Qt)
        if self.base is not None:
            self.base.salvar()
            # Sem espaço ou sem permissão, o backup não sai, mas os dados já estão gravados.
            with suppress(OSError):
                backup_ao_fechar(self.base, self.caminho)  # RF22
            self.base.conexao.close()
            self.base = None
        super().closeEvent(evento)
