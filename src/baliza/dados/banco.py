"""Base de dados do Baliza: SQLite na memória, gravado no disco só pelo Cofre (cifrado).

A estrutura é versionada com `PRAGMA user_version`. Cada item de MIGRACOES leva a base de uma
versão para a seguinte; versões novas do Baliza só acrescentam itens ao fim da lista.
"""

from __future__ import annotations

import os
import sqlite3

from baliza.dados.cofre import Cofre

MIGRACOES: list[str] = [
    # 1 · lista de bancos (RN13)
    """
    CREATE TABLE banco (
        codigo TEXT PRIMARY KEY,
        ispb   TEXT,
        nome   TEXT NOT NULL,
        origem TEXT NOT NULL CHECK (origem IN ('oficial', 'manual'))
    );
    """,
]


def versao_atual() -> int:
    return len(MIGRACOES)


class BaseDeDados:
    """Base aberta. Use `salvar()` para gravar as alterações no arquivo cifrado."""

    def __init__(self, cofre: Cofre, conexao: sqlite3.Connection) -> None:
        self.cofre = cofre
        self.conexao = conexao

    @classmethod
    def criar(cls, caminho: str | os.PathLike, senha: str) -> tuple[BaseDeDados, str]:
        """Cria a base num arquivo novo. Devolve a base e a chave de recuperação."""
        from baliza.dados.lista_bancos import carregar_bancos_oficiais

        cofre, chave = Cofre.criar(caminho, senha)
        base = cls(cofre, sqlite3.connect(":memory:"))
        base.migrar()
        carregar_bancos_oficiais(base.conexao)
        base.salvar()
        return base, chave

    @classmethod
    def abrir(
        cls, caminho: str | os.PathLike, *, senha: str | None = None, chave: str | None = None
    ) -> BaseDeDados:
        if (senha is None) == (chave is None):
            raise ValueError("Informe a senha ou a chave de recuperação.")
        cofre = (
            Cofre.abrir_com_senha(caminho, senha)
            if senha is not None
            else Cofre.abrir_com_chave(caminho, chave)
        )
        conexao = sqlite3.connect(":memory:")
        conteudo = cofre.ler()
        if conteudo:
            conexao.deserialize(conteudo)
        base = cls(cofre, conexao)
        if base.versao() != versao_atual():
            base.migrar()
            base.salvar()
        return base

    def versao(self) -> int:
        return self.conexao.execute("PRAGMA user_version").fetchone()[0]

    def migrar(self) -> None:
        atual = self.versao()
        if atual > versao_atual():
            raise RuntimeError(
                "Estes dados foram gravados por uma versão mais nova do Baliza. "
                "Atualize o sistema para abri-los."
            )
        for numero, script in enumerate(MIGRACOES[atual:], start=atual + 1):
            with self.conexao:
                self.conexao.executescript(script)
                self.conexao.execute(f"PRAGMA user_version = {numero}")

    def salvar(self) -> None:
        self.conexao.commit()
        self.cofre.gravar(self.conexao.serialize())

    def fechar(self) -> None:
        self.salvar()
        self.conexao.close()
