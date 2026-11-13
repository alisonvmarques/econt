"""Fornecedores (RF07, RF08), suas contas bancárias (RF09) e chaves Pix (RF10)."""

from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime

from econt.dados.contas import FORMATO_AGENCIA, FORMATO_CONTA
from econt.dados.lista_bancos import obter_banco
from econt.dominio.documentos import (
    NOME_DO_DOCUMENTO,
    TIPOS_DE_PESSOA,
    formatar_documento,
    problema_do_documento,
    somente_caracteres,
)
from econt.dominio.pix import (
    EMAIL,
    TIPOS_DE_CHAVE,
    ChaveInvalida,
    formatar_chave,
    normalizar_chave,
)

TIPOS_DE_CONTA = {"corrente": "Conta corrente", "poupanca": "Poupança", "pagamento": "Pagamento"}


class FornecedorInvalido(ValueError):
    pass


class ExclusaoNaoPermitida(ValueError):
    pass


def _agora() -> str:
    return datetime.now().replace(microsecond=0).isoformat()


# Fornecedor ------------------------------------------------------------------------------


@dataclass
class DadosFornecedor:
    """O que se digita no formulário do fornecedor."""

    tipo: str
    documento: str
    razao_social: str
    nome_fantasia: str = ""
    telefone: str = ""
    email: str = ""
    endereco: str = ""
    observacoes: str = ""


@dataclass
class Fornecedor(DadosFornecedor):
    id: int = 0
    ativo: bool = True
    criado_em: str = ""
    alterado_em: str = ""
    contas_e_chaves: int = 0

    @property
    def documento_formatado(self) -> str:
        return formatar_documento(self.tipo, self.documento)

    @property
    def nome_do_documento(self) -> str:
        return NOME_DO_DOCUMENTO[self.tipo]

    @property
    def nome_do_tipo(self) -> str:
        return TIPOS_DE_PESSOA[self.tipo]

    def dados(self) -> DadosFornecedor:
        return DadosFornecedor(
            self.tipo,
            self.documento,
            self.razao_social,
            self.nome_fantasia,
            self.telefone,
            self.email,
            self.endereco,
            self.observacoes,
        )


def problemas_do_fornecedor(
    conexao: sqlite3.Connection, dados: DadosFornecedor, ignorar_id: int | None = None
) -> dict[str, str]:
    """Erros por campo, em português. Vazio quando está tudo certo."""
    erros = {}
    if dados.tipo not in TIPOS_DE_PESSOA:
        erros["tipo"] = "Escolha pessoa jurídica ou pessoa física."
        return erros
    if problema := problema_do_documento(dados.tipo, dados.documento):
        erros["documento"] = problema
    else:
        outro = conexao.execute(
            "SELECT razao_social FROM fornecedor WHERE documento = ? AND id IS NOT ?",
            (somente_caracteres(dados.documento), ignorar_id),
        ).fetchone()
        if outro:
            erros["documento"] = f"Este {NOME_DO_DOCUMENTO[dados.tipo]} já é de {outro[0]}."
    if not dados.razao_social.strip():
        erros["razao_social"] = (
            "Informe a razão social." if dados.tipo == "pj" else "Informe o nome."
        )
    if dados.email.strip() and not EMAIL.fullmatch(dados.email.strip()):
        erros["email"] = "E-mail inválido. Escreva assim: contato@exemplo.com.br."
    if ignorar_id is not None and "documento" not in erros:
        documento = somente_caracteres(dados.documento)
        chave_de_outro = conexao.execute(
            "SELECT count(*) FROM chave_pix WHERE fornecedor_id = ? AND tipo IN ('cpf', 'cnpj')"
            " AND chave <> ?",
            (ignorar_id, documento),
        ).fetchone()[0]
        if chave_de_outro:
            erros["documento"] = (
                "Há chave Pix de CPF ou CNPJ com o documento anterior. Exclua essa chave antes "
                "de trocar o documento."
            )
    return erros


def _valores(dados: DadosFornecedor) -> tuple:
    return (
        dados.tipo,
        somente_caracteres(dados.documento),
        dados.razao_social.strip(),
        dados.nome_fantasia.strip() if dados.tipo == "pj" else "",
        dados.telefone.strip(),
        dados.email.strip(),
        dados.endereco.strip(),
        dados.observacoes.strip(),
    )


def cadastrar_fornecedor(conexao: sqlite3.Connection, dados: DadosFornecedor) -> int:
    erros = problemas_do_fornecedor(conexao, dados)
    if erros:
        raise FornecedorInvalido(" ".join(erros.values()))
    agora = _agora()
    with conexao:
        cursor = conexao.execute(
            """
            INSERT INTO fornecedor (tipo, documento, razao_social, nome_fantasia, telefone,
                email, endereco, observacoes, criado_em, alterado_em)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (*_valores(dados), agora, agora),
        )
    return cursor.lastrowid


def editar_fornecedor(conexao: sqlite3.Connection, fornecedor_id: int, dados: DadosFornecedor):
    erros = problemas_do_fornecedor(conexao, dados, ignorar_id=fornecedor_id)
    if erros:
        raise FornecedorInvalido(" ".join(erros.values()))
    with conexao:
        conexao.execute(
            """
            UPDATE fornecedor SET tipo = ?, documento = ?, razao_social = ?, nome_fantasia = ?,
                telefone = ?, email = ?, endereco = ?, observacoes = ?, alterado_em = ?
            WHERE id = ?
            """,
            (*_valores(dados), _agora(), fornecedor_id),
        )


_SELECAO_FORNECEDOR = """
    SELECT f.tipo, f.documento, f.razao_social, f.nome_fantasia, f.telefone, f.email,
        f.endereco, f.observacoes, f.id, f.ativo, f.criado_em, f.alterado_em,
        (SELECT count(*) FROM conta_fornecedor c WHERE c.fornecedor_id = f.id)
        + (SELECT count(*) FROM chave_pix p WHERE p.fornecedor_id = f.id)
    FROM fornecedor f
"""


def _fornecedor(linha: tuple) -> Fornecedor:
    *dados, fornecedor_id, ativo, criado_em, alterado_em, quantos = linha
    return Fornecedor(*dados, fornecedor_id, bool(ativo), criado_em, alterado_em, quantos)


def obter_fornecedor(conexao: sqlite3.Connection, fornecedor_id: int) -> Fornecedor:
    linha = conexao.execute(_SELECAO_FORNECEDOR + " WHERE f.id = ?", (fornecedor_id,)).fetchone()
    if linha is None:
        raise FornecedorInvalido("Fornecedor não encontrado.")
    return _fornecedor(linha)


def listar_fornecedores(
    conexao: sqlite3.Connection, busca: str = "", incluir_inativos: bool = False
) -> list[Fornecedor]:
    """Busca pelo nome (razão social ou fantasia) e pelo CNPJ/CPF, com ou sem pontuação."""
    termo = busca.strip().lower()
    documento = somente_caracteres(busca)
    linhas = conexao.execute(
        _SELECAO_FORNECEDOR
        + """
        WHERE (? OR f.ativo = 1)
          AND (? = '' OR lower(f.razao_social) LIKE ? OR lower(f.nome_fantasia) LIKE ?
               OR (? <> '' AND f.documento LIKE ?))
        ORDER BY f.ativo DESC, f.razao_social COLLATE NOCASE
        """,
        (incluir_inativos, termo, f"%{termo}%", f"%{termo}%", documento, f"%{documento}%"),
    ).fetchall()
    return [_fornecedor(linha) for linha in linhas]


def tem_historico(conexao: sqlite3.Connection, fornecedor_id: int) -> bool:
    """Histórico de cadastros = alguma marcação numa conta ou chave do fornecedor (RN05)."""
    return bool(
        conexao.execute(
            """
            SELECT count(*) FROM marcacao m
            LEFT JOIN conta_fornecedor c ON c.id = m.conta_fornecedor_id
            LEFT JOIN chave_pix p ON p.id = m.chave_pix_id
            WHERE c.fornecedor_id = ? OR p.fornecedor_id = ?
            """,
            (fornecedor_id, fornecedor_id),
        ).fetchone()[0]
    )


def definir_fornecedor_ativo(conexao: sqlite3.Connection, fornecedor_id: int, ativo: bool):
    """Inativar não apaga contas, chaves nem marcações (RN12)."""
    with conexao:
        conexao.execute(
            "UPDATE fornecedor SET ativo = ?, alterado_em = ? WHERE id = ?",
            (int(ativo), _agora(), fornecedor_id),
        )


def excluir_fornecedor(conexao: sqlite3.Connection, fornecedor_id: int) -> None:
    """Só sem histórico de cadastros; com histórico, apenas inativar (RN05).

    As atividades ligadas a ele continuam no quadro, só sem o vínculo (RN18)."""
    if tem_historico(conexao, fornecedor_id):
        raise ExclusaoNaoPermitida(
            "Este fornecedor tem histórico de cadastros e não pode ser excluído. Inative-o."
        )
    with conexao:
        conexao.execute("DELETE FROM conta_fornecedor WHERE fornecedor_id = ?", (fornecedor_id,))
        conexao.execute("DELETE FROM chave_pix WHERE fornecedor_id = ?", (fornecedor_id,))
        conexao.execute(
            "UPDATE atividade SET fornecedor_id = NULL WHERE fornecedor_id = ?", (fornecedor_id,)
        )
        conexao.execute("DELETE FROM fornecedor WHERE id = ?", (fornecedor_id,))


# Contas bancárias do fornecedor ----------------------------------------------------------


@dataclass
class DadosContaFornecedor:
    banco: str
    agencia: str
    conta: str
    tipo: str = "corrente"


@dataclass
class ContaFornecedor(DadosContaFornecedor):
    id: int = 0
    fornecedor_id: int = 0
    banco_nome: str = ""
    ativa: bool = True

    @property
    def nome_do_tipo(self) -> str:
        return TIPOS_DE_CONTA[self.tipo]

    @property
    def banco_rotulo(self) -> str:
        return f"{self.banco} · {self.banco_nome}"

    def dados(self) -> DadosContaFornecedor:
        return DadosContaFornecedor(self.banco, self.agencia, self.conta, self.tipo)


def _limpar(texto: str) -> str:
    return re.sub(r"\s", "", texto).upper()


def problemas_da_conta_fornecedor(
    conexao: sqlite3.Connection,
    fornecedor_id: int,
    dados: DadosContaFornecedor,
    ignorar_id: int | None = None,
) -> dict[str, str]:
    erros = {}
    agencia, conta = _limpar(dados.agencia), _limpar(dados.conta)
    if not dados.banco:
        erros["banco"] = "Escolha o banco."
    elif obter_banco(conexao, dados.banco) is None:
        erros["banco"] = "Banco não encontrado. Escolha um banco da lista."
    if not agencia:
        erros["agencia"] = "Informe a agência."
    elif not FORMATO_AGENCIA.fullmatch(agencia):
        erros["agencia"] = "Agência com até 5 números e o dígito, se houver, assim: 1234-5."
    if not conta:
        erros["conta"] = "Informe a conta com o dígito."
    elif not FORMATO_CONTA.fullmatch(conta):
        erros["conta"] = "Informe a conta com o dígito depois do traço, assim: 98765-4."
    if dados.tipo not in TIPOS_DE_CONTA:
        erros["tipo"] = "Escolha o tipo da conta."
    if (
        not erros
        and conexao.execute(
            "SELECT 1 FROM conta_fornecedor WHERE fornecedor_id = ? AND banco = ? AND agencia = ?"
            " AND conta = ? AND id IS NOT ?",
            (fornecedor_id, dados.banco, agencia, conta, ignorar_id),
        ).fetchone()
    ):
        erros["conta"] = "Esta conta já está cadastrada neste fornecedor."
    return erros


def outros_fornecedores_com_a_conta(
    conexao: sqlite3.Connection, fornecedor_id: int, dados: DadosContaFornecedor
) -> list[str]:
    """Para o aviso: a mesma conta já existe em outro fornecedor."""
    linhas = conexao.execute(
        """
        SELECT f.razao_social FROM conta_fornecedor c JOIN fornecedor f ON f.id = c.fornecedor_id
        WHERE c.banco = ? AND c.agencia = ? AND c.conta = ? AND c.fornecedor_id <> ?
        ORDER BY f.razao_social
        """,
        (dados.banco, _limpar(dados.agencia), _limpar(dados.conta), fornecedor_id),
    ).fetchall()
    return [linha[0] for linha in linhas]


def salvar_conta_fornecedor(
    conexao: sqlite3.Connection,
    fornecedor_id: int,
    dados: DadosContaFornecedor,
    conta_id: int | None = None,
) -> int:
    """A conta é sempre do próprio fornecedor (RN10): não existe titular diferente."""
    erros = problemas_da_conta_fornecedor(conexao, fornecedor_id, dados, conta_id)
    if erros:
        raise FornecedorInvalido(" ".join(erros.values()))
    valores = (dados.banco, _limpar(dados.agencia), _limpar(dados.conta), dados.tipo)
    agora = _agora()
    with conexao:
        if conta_id is None:
            cursor = conexao.execute(
                """
                INSERT INTO conta_fornecedor (fornecedor_id, banco, agencia, conta, tipo,
                    criado_em, alterado_em)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (fornecedor_id, *valores, agora, agora),
            )
            conta_id = cursor.lastrowid
        else:
            conexao.execute(
                "UPDATE conta_fornecedor SET banco = ?, agencia = ?, conta = ?, tipo = ?,"
                " alterado_em = ? WHERE id = ?",
                (*valores, agora, conta_id),
            )
        conexao.execute(
            "UPDATE fornecedor SET alterado_em = ? WHERE id = ?", (agora, fornecedor_id)
        )
    return conta_id


def listar_contas_fornecedor(
    conexao: sqlite3.Connection, fornecedor_id: int
) -> list[ContaFornecedor]:
    linhas = conexao.execute(
        """
        SELECT c.banco, c.agencia, c.conta, c.tipo, c.id, c.fornecedor_id, b.nome, c.ativa
        FROM conta_fornecedor c JOIN banco b ON b.codigo = c.banco
        WHERE c.fornecedor_id = ? ORDER BY c.ativa DESC, c.banco, c.agencia, c.conta
        """,
        (fornecedor_id,),
    ).fetchall()
    return [ContaFornecedor(*linha[:7], bool(linha[7])) for linha in linhas]


# Chaves Pix do fornecedor ----------------------------------------------------------------


@dataclass
class ChavePix:
    tipo: str
    chave: str
    id: int = 0
    fornecedor_id: int = 0
    ativa: bool = True

    @property
    def nome_do_tipo(self) -> str:
        return TIPOS_DE_CHAVE[self.tipo]

    @property
    def chave_formatada(self) -> str:
        return formatar_chave(self.tipo, self.chave)


def problema_da_chave(
    conexao: sqlite3.Connection,
    fornecedor: Fornecedor,
    tipo: str,
    chave: str,
    ignorar_id: int | None = None,
) -> str | None:
    try:
        normalizada = normalizar_chave(tipo, chave)
    except ChaveInvalida as erro:
        return str(erro)
    if tipo in ("cpf", "cnpj"):
        if tipo != {"pf": "cpf", "pj": "cnpj"}[fornecedor.tipo]:
            return (
                f"Este fornecedor é {fornecedor.nome_do_tipo.lower()}: a chave de documento é o "
                f"{fornecedor.nome_do_documento} dele."
            )
        if normalizada != fornecedor.documento:
            return (
                f"A chave precisa ser o {fornecedor.nome_do_documento} do próprio fornecedor "
                f"({fornecedor.documento_formatado})."
            )
    if conexao.execute(
        "SELECT 1 FROM chave_pix WHERE fornecedor_id = ? AND tipo = ? AND chave = ?"
        " AND id IS NOT ?",
        (fornecedor.id, tipo, normalizada, ignorar_id),
    ).fetchone():
        return "Esta chave já está cadastrada neste fornecedor."
    return None


def outros_fornecedores_com_a_chave(
    conexao: sqlite3.Connection, fornecedor_id: int, tipo: str, chave: str
) -> list[str]:
    try:
        normalizada = normalizar_chave(tipo, chave)
    except ChaveInvalida:
        return []
    linhas = conexao.execute(
        """
        SELECT f.razao_social FROM chave_pix p JOIN fornecedor f ON f.id = p.fornecedor_id
        WHERE p.tipo = ? AND p.chave = ? AND p.fornecedor_id <> ? ORDER BY f.razao_social
        """,
        (tipo, normalizada, fornecedor_id),
    ).fetchall()
    return [linha[0] for linha in linhas]


def salvar_chave_pix(
    conexao: sqlite3.Connection,
    fornecedor_id: int,
    tipo: str,
    chave: str,
    chave_id: int | None = None,
) -> int:
    fornecedor = obter_fornecedor(conexao, fornecedor_id)
    if problema := problema_da_chave(conexao, fornecedor, tipo, chave, chave_id):
        raise ChaveInvalida(problema)
    normalizada = normalizar_chave(tipo, chave)
    agora = _agora()
    with conexao:
        if chave_id is None:
            cursor = conexao.execute(
                "INSERT INTO chave_pix (fornecedor_id, tipo, chave, criado_em, alterado_em)"
                " VALUES (?, ?, ?, ?, ?)",
                (fornecedor_id, tipo, normalizada, agora, agora),
            )
            chave_id = cursor.lastrowid
        else:
            conexao.execute(
                "UPDATE chave_pix SET tipo = ?, chave = ?, alterado_em = ? WHERE id = ?",
                (tipo, normalizada, agora, chave_id),
            )
        conexao.execute(
            "UPDATE fornecedor SET alterado_em = ? WHERE id = ?", (agora, fornecedor_id)
        )
    return chave_id


def listar_chaves(conexao: sqlite3.Connection, fornecedor_id: int) -> list[ChavePix]:
    linhas = conexao.execute(
        "SELECT tipo, chave, id, fornecedor_id, ativa FROM chave_pix WHERE fornecedor_id = ?"
        " ORDER BY ativa DESC, id",
        (fornecedor_id,),
    ).fetchall()
    return [ChavePix(t, c, i, f, bool(a)) for t, c, i, f, a in linhas]


# Exclusão de conta ou chave --------------------------------------------------------------


TABELAS_DE_ITENS = {"conta_fornecedor": "conta_fornecedor_id", "chave_pix": "chave_pix_id"}


def _coluna(tabela: str) -> str:
    """Só as duas tabelas conhecidas entram no SQL."""
    if tabela not in TABELAS_DE_ITENS:
        raise ValueError(f"Tabela desconhecida: {tabela}")
    return TABELAS_DE_ITENS[tabela]


def item_tem_historico(conexao: sqlite3.Connection, tabela: str, item_id: int) -> bool:
    coluna = _coluna(tabela)
    return bool(
        conexao.execute(f"SELECT count(*) FROM marcacao WHERE {coluna} = ?", (item_id,)).fetchone()[
            0
        ]
    )


def excluir_item(conexao: sqlite3.Connection, tabela: str, item_id: int) -> None:
    """Conta ou chave do fornecedor: excluir só sem histórico de cadastros (RN05)."""
    if item_tem_historico(conexao, tabela, item_id):
        raise ExclusaoNaoPermitida("Tem histórico de cadastros e não pode ser excluída. Inative.")
    _coluna(tabela)
    with conexao:
        conexao.execute(f"DELETE FROM {tabela} WHERE id = ?", (item_id,))


def definir_item_ativo(conexao: sqlite3.Connection, tabela: str, item_id: int, ativo: bool):
    """Inativar não apaga as marcações; elas voltam na reativação (RN12)."""
    _coluna(tabela)
    with conexao:
        conexao.execute(
            f"UPDATE {tabela} SET ativa = ?, alterado_em = ? WHERE id = ?",
            (int(ativo), _agora(), item_id),
        )
