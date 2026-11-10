"""Base de dados do ECont: SQLite na memória, gravado no disco só pelo Cofre (cifrado).

A estrutura é versionada com `PRAGMA user_version`. Cada item de MIGRACOES leva a base de uma
versão para a seguinte; versões novas do ECont só acrescentam itens ao fim da lista.
"""

from __future__ import annotations

import os
import sqlite3

from econt.dados.cofre import Cofre

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
    # 2 · dados da entidade: uma única entidade (RN09), garantida pelo id fixo
    """
    CREATE TABLE entidade (
        id           INTEGER PRIMARY KEY CHECK (id = 1),
        razao_social TEXT NOT NULL,
        cnpj         TEXT NOT NULL,
        logo         BLOB,
        criado_em    TEXT NOT NULL,
        alterado_em  TEXT NOT NULL
    );
    """,
    # 3 · configurações do sistema (chave/valor)
    """
    CREATE TABLE configuracao (
        chave TEXT PRIMARY KEY,
        valor TEXT NOT NULL
    );
    """,
    # 4 · contas da entidade (RF17) e pedidos de alteração de limite (RF18, RN06, RN07, RN11).
    # Os limites são da conta da entidade, nunca do fornecedor. Valores em centavos.
    """
    CREATE TABLE conta_entidade (
        id               INTEGER PRIMARY KEY,
        descricao        TEXT NOT NULL,
        banco            TEXT NOT NULL REFERENCES banco (codigo),
        agencia          TEXT NOT NULL,
        conta            TEXT NOT NULL,
        limite_pix       INTEGER NOT NULL,
        limite_transacao INTEGER NOT NULL,
        ativa            INTEGER NOT NULL DEFAULT 1,
        criado_em        TEXT NOT NULL,
        alterado_em      TEXT NOT NULL,
        UNIQUE (banco, agencia, conta)
    );
    CREATE TABLE pedido_limite (
        id        INTEGER PRIMARY KEY,
        conta_id  INTEGER NOT NULL REFERENCES conta_entidade (id),
        tipo      TEXT NOT NULL CHECK (tipo IN ('pix', 'transacao')),
        valor     INTEGER NOT NULL CHECK (valor > 0),
        pedido_em TEXT NOT NULL,
        criado_em TEXT NOT NULL
    );
    CREATE INDEX pedido_limite_conta ON pedido_limite (conta_id, tipo, pedido_em);
    """,
    # 5 · fornecedores (RF07, RF08, RN03), suas contas (RF09, RN10) e chaves Pix (RF10, RN02),
    # e as marcações de onde cada conta e chave está cadastrada (RF11, preenchidas a partir da
    # v0.5). Uma marcação é o histórico que impede excluir (RN05).
    """
    CREATE TABLE fornecedor (
        id            INTEGER PRIMARY KEY,
        tipo          TEXT NOT NULL CHECK (tipo IN ('pj', 'pf')),
        documento     TEXT NOT NULL UNIQUE,
        razao_social  TEXT NOT NULL,
        nome_fantasia TEXT NOT NULL DEFAULT '',
        telefone      TEXT NOT NULL DEFAULT '',
        email         TEXT NOT NULL DEFAULT '',
        endereco      TEXT NOT NULL DEFAULT '',
        observacoes   TEXT NOT NULL DEFAULT '',
        ativo         INTEGER NOT NULL DEFAULT 1,
        criado_em     TEXT NOT NULL,
        alterado_em   TEXT NOT NULL
    );
    CREATE TABLE conta_fornecedor (
        id            INTEGER PRIMARY KEY,
        fornecedor_id INTEGER NOT NULL REFERENCES fornecedor (id),
        banco         TEXT NOT NULL REFERENCES banco (codigo),
        agencia       TEXT NOT NULL,
        conta         TEXT NOT NULL,
        tipo          TEXT NOT NULL CHECK (tipo IN ('corrente', 'poupanca', 'pagamento')),
        ativa         INTEGER NOT NULL DEFAULT 1,
        criado_em     TEXT NOT NULL,
        alterado_em   TEXT NOT NULL,
        UNIQUE (fornecedor_id, banco, agencia, conta)
    );
    CREATE TABLE chave_pix (
        id            INTEGER PRIMARY KEY,
        fornecedor_id INTEGER NOT NULL REFERENCES fornecedor (id),
        tipo          TEXT NOT NULL
                      CHECK (tipo IN ('cnpj', 'cpf', 'email', 'telefone', 'aleatoria')),
        chave         TEXT NOT NULL,
        ativa         INTEGER NOT NULL DEFAULT 1,
        criado_em     TEXT NOT NULL,
        alterado_em   TEXT NOT NULL,
        UNIQUE (fornecedor_id, tipo, chave)
    );
    CREATE TABLE marcacao (
        id                  INTEGER PRIMARY KEY,
        conta_entidade_id   INTEGER NOT NULL REFERENCES conta_entidade (id),
        conta_fornecedor_id INTEGER REFERENCES conta_fornecedor (id),
        chave_pix_id        INTEGER REFERENCES chave_pix (id),
        criado_em           TEXT NOT NULL,
        CHECK ((conta_fornecedor_id IS NULL) <> (chave_pix_id IS NULL)),
        UNIQUE (conta_entidade_id, conta_fornecedor_id, chave_pix_id)
    );
    """,
    # 6 · desmarcar não apaga a marcação: guarda quando foi desmarcada, e o histórico de
    # cadastros continua valendo para a regra de exclusão (RN05).
    """
    ALTER TABLE marcacao ADD COLUMN desmarcada_em TEXT;
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
        from econt.dados.lista_bancos import carregar_bancos_oficiais

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
                "Estes dados foram gravados por uma versão mais nova do ECont. "
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

    def configuracao(self, chave: str, padrao: str | None = None) -> str | None:
        linha = self.conexao.execute(
            "SELECT valor FROM configuracao WHERE chave = ?", (chave,)
        ).fetchone()
        return linha[0] if linha else padrao

    def definir_configuracao(self, chave: str, valor: str) -> None:
        with self.conexao:
            self.conexao.execute(
                "INSERT INTO configuracao (chave, valor) VALUES (?, ?) "
                "ON CONFLICT (chave) DO UPDATE SET valor = excluded.valor",
                (chave, valor),
            )
