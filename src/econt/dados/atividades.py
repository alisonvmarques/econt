"""Quadro de atividades da entidade: colunas (RF27), atividades (RF28 a RF31), etiquetas
(RF32) e prioridade (RF33).

As posições são inteiros a partir de 1, sem buracos, entre as atividades ativas de cada
coluna (RN16). Toda mudança que mexe em posições roda numa transação: se algo falha, nada
muda. As funções que dependem da data recebem `hoje`, para os testes controlarem o dia.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from datetime import date, datetime

from econt.dominio.atividades import (
    ATRASADA,
    CONCLUIDA,
    CORES_DE_ETIQUETA,
    PRIORIDADES,
    VENCE_HOJE,
    AtividadeInvalida,
    problema_do_nome_da_coluna,
    problema_do_nome_da_etiqueta,
    problema_do_titulo,
    situacao_do_prazo,
)
from econt.dominio.texto import encontrar

COLUNA_EXCLUIDA = "(coluna excluída)"


class ColunaInvalida(ValueError):
    pass


def _agora() -> str:
    return datetime.now().replace(microsecond=0).isoformat()


def _data(texto: str | None) -> datetime | None:
    return datetime.fromisoformat(texto) if texto else None


# Colunas ---------------------------------------------------------------------------------


@dataclass
class Coluna:
    id: int
    nome: str
    posicao: int
    conclusao: bool


def listar_colunas(conexao: sqlite3.Connection) -> list[Coluna]:
    linhas = conexao.execute(
        "SELECT id, nome, posicao, conclusao FROM coluna_atividade ORDER BY posicao, id"
    ).fetchall()
    return [Coluna(i, nome, posicao, bool(conclusao)) for i, nome, posicao, conclusao in linhas]


def obter_coluna(conexao: sqlite3.Connection, coluna_id: int) -> Coluna:
    for coluna in listar_colunas(conexao):
        if coluna.id == coluna_id:
            return coluna
    raise ColunaInvalida("Coluna não encontrada. Feche a janela e abra o quadro de novo.")


def problema_da_coluna(
    conexao: sqlite3.Connection, nome: str, ignorar_id: int | None = None
) -> str | None:
    outros = [c.nome for c in listar_colunas(conexao) if c.id != ignorar_id]
    return problema_do_nome_da_coluna(nome, outros)


def _validar_nome(conexao: sqlite3.Connection, nome: str, ignorar_id: int | None = None) -> str:
    if erro := problema_da_coluna(conexao, nome, ignorar_id):
        raise ColunaInvalida(erro)
    return nome.strip()


def _renumerar_colunas(conexao: sqlite3.Connection, ordem: list[int]) -> None:
    for posicao, coluna_id in enumerate(ordem, start=1):
        conexao.execute(
            "UPDATE coluna_atividade SET posicao = ? WHERE id = ?", (posicao, coluna_id)
        )


def criar_coluna(conexao: sqlite3.Connection, nome: str, conclusao: bool = False) -> int:
    """A coluna nova entra à direita das outras."""
    nome = _validar_nome(conexao, nome)
    agora = _agora()
    with conexao:
        posicao = conexao.execute(
            "SELECT coalesce(max(posicao), 0) + 1 FROM coluna_atividade"
        ).fetchone()[0]
        cursor = conexao.execute(
            "INSERT INTO coluna_atividade (nome, posicao, criado_em, alterado_em)"
            " VALUES (?, ?, ?, ?)",
            (nome, posicao, agora, agora),
        )
        if conclusao:
            _marcar_conclusao(conexao, cursor.lastrowid, True)
    return cursor.lastrowid


def renomear_coluna(conexao: sqlite3.Connection, coluna_id: int, nome: str) -> None:
    obter_coluna(conexao, coluna_id)
    nome = _validar_nome(conexao, nome, ignorar_id=coluna_id)
    with conexao:
        conexao.execute(
            "UPDATE coluna_atividade SET nome = ?, alterado_em = ? WHERE id = ?",
            (nome, _agora(), coluna_id),
        )


def mover_coluna(conexao: sqlite3.Connection, coluna_id: int, posicao: int) -> None:
    """Mesma ideia das atividades: posição fora do intervalo vira a primeira ou a última."""
    obter_coluna(conexao, coluna_id)
    with conexao:
        ordem = [c.id for c in listar_colunas(conexao) if c.id != coluna_id]
        posicao = min(max(posicao, 1), len(ordem) + 1)
        ordem.insert(posicao - 1, coluna_id)
        _renumerar_colunas(conexao, ordem)


def _marcar_conclusao(conexao: sqlite3.Connection, coluna_id: int, conclusao: bool) -> None:
    agora = _agora()
    conexao.execute(
        "UPDATE coluna_atividade SET conclusao = 0, alterado_em = ? WHERE conclusao = 1",
        (agora,),
    )
    if conclusao:
        conexao.execute(
            "UPDATE coluna_atividade SET conclusao = 1, alterado_em = ? WHERE id = ?",
            (agora, coluna_id),
        )


def definir_conclusao(conexao: sqlite3.Connection, coluna_id: int, conclusao: bool) -> None:
    """RN15: no máximo uma coluna de conclusão. Marcar uma desmarca a que era antes."""
    coluna = obter_coluna(conexao, coluna_id)
    if coluna.conclusao == conclusao:
        return
    with conexao:
        if conclusao:
            _marcar_conclusao(conexao, coluna_id, True)
        else:
            conexao.execute(
                "UPDATE coluna_atividade SET conclusao = 0, alterado_em = ? WHERE id = ?",
                (_agora(), coluna_id),
            )


def coluna_de_conclusao(conexao: sqlite3.Connection) -> Coluna | None:
    return next((c for c in listar_colunas(conexao) if c.conclusao), None)


def excluir_coluna(conexao: sqlite3.Connection, coluna_id: int) -> None:
    """RN14: só coluna vazia (nem ativas nem arquivadas), e o quadro fica com uma, no mínimo."""
    coluna = obter_coluna(conexao, coluna_id)
    ativas, arquivadas = conexao.execute(
        "SELECT count(*) FILTER (WHERE arquivado_em IS NULL),"
        " count(*) FILTER (WHERE arquivado_em IS NOT NULL)"
        " FROM atividade WHERE coluna_id = ?",
        (coluna_id,),
    ).fetchone()
    if ativas or arquivadas:
        partes = []
        if ativas:
            partes.append(f"{ativas} {'atividade' if ativas == 1 else 'atividades'} no quadro")
        if arquivadas:
            partes.append(f"{arquivadas} {'arquivada' if arquivadas == 1 else 'arquivadas'}")
        raise ColunaInvalida(
            f"A coluna {coluna.nome} tem {' e '.join(partes)}. Mova ou exclua as atividades "
            "antes de excluir a coluna."
        )
    colunas = listar_colunas(conexao)
    if len(colunas) == 1:
        raise ColunaInvalida(
            "O quadro precisa de pelo menos uma coluna. Crie outra antes de excluir esta."
        )
    with conexao:
        conexao.execute("DELETE FROM coluna_atividade WHERE id = ?", (coluna_id,))
        _renumerar_colunas(conexao, [c.id for c in colunas if c.id != coluna_id])


# Etiquetas -------------------------------------------------------------------------------


class EtiquetaInvalida(ValueError):
    pass


@dataclass
class Etiqueta:
    id: int
    nome: str
    cor: str

    @property
    def nome_da_cor(self) -> str:
        return CORES_DE_ETIQUETA.get(self.cor, "")


def listar_etiquetas(conexao: sqlite3.Connection) -> list[Etiqueta]:
    linhas = conexao.execute(
        "SELECT id, nome, cor FROM etiqueta ORDER BY nome COLLATE NOCASE, id"
    ).fetchall()
    return [Etiqueta(*linha) for linha in linhas]


def obter_etiqueta(conexao: sqlite3.Connection, etiqueta_id: int) -> Etiqueta:
    linha = conexao.execute(
        "SELECT id, nome, cor FROM etiqueta WHERE id = ?", (etiqueta_id,)
    ).fetchone()
    if linha is None:
        raise EtiquetaInvalida("Etiqueta não encontrada. Feche a janela e abra de novo.")
    return Etiqueta(*linha)


def problema_da_etiqueta(
    conexao: sqlite3.Connection, nome: str, ignorar_id: int | None = None
) -> str | None:
    outros = [e.nome for e in listar_etiquetas(conexao) if e.id != ignorar_id]
    return problema_do_nome_da_etiqueta(nome, outros)


def _validar_etiqueta(
    conexao: sqlite3.Connection, nome: str, cor: str, ignorar_id: int | None = None
) -> tuple[str, str]:
    if erro := problema_da_etiqueta(conexao, nome, ignorar_id):
        raise EtiquetaInvalida(erro)
    if cor not in CORES_DE_ETIQUETA:
        raise EtiquetaInvalida("Escolha a cor da etiqueta na lista.")
    return nome.strip(), cor


def criar_etiqueta(conexao: sqlite3.Connection, nome: str, cor: str = "neutra") -> int:
    nome, cor = _validar_etiqueta(conexao, nome, cor)
    agora = _agora()
    with conexao:
        cursor = conexao.execute(
            "INSERT INTO etiqueta (nome, cor, criado_em, alterado_em) VALUES (?, ?, ?, ?)",
            (nome, cor, agora, agora),
        )
    return cursor.lastrowid


def editar_etiqueta(conexao: sqlite3.Connection, etiqueta_id: int, nome: str, cor: str) -> None:
    obter_etiqueta(conexao, etiqueta_id)
    nome, cor = _validar_etiqueta(conexao, nome, cor, etiqueta_id)
    with conexao:
        conexao.execute(
            "UPDATE etiqueta SET nome = ?, cor = ?, alterado_em = ? WHERE id = ?",
            (nome, cor, _agora(), etiqueta_id),
        )


def atividades_com_etiqueta(conexao: sqlite3.Connection, etiqueta_id: int) -> int:
    """Quantas atividades, no quadro ou arquivadas, usam a etiqueta."""
    return conexao.execute(
        "SELECT count(*) FROM atividade_etiqueta WHERE etiqueta_id = ?", (etiqueta_id,)
    ).fetchone()[0]


def excluir_etiqueta(conexao: sqlite3.Connection, etiqueta_id: int) -> None:
    """Sai das atividades que a usam; as atividades continuam como estão (RN19)."""
    obter_etiqueta(conexao, etiqueta_id)
    with conexao:
        conexao.execute("DELETE FROM atividade_etiqueta WHERE etiqueta_id = ?", (etiqueta_id,))
        conexao.execute("DELETE FROM etiqueta WHERE id = ?", (etiqueta_id,))


def _etiquetas_das_atividades(conexao: sqlite3.Connection, atividades: list[Atividade]) -> None:
    """Preenche as etiquetas de cada atividade, numa consulta só."""
    if not atividades:
        return
    por_id = {a.id: a for a in atividades}
    marcas = ",".join("?" * len(por_id))
    linhas = conexao.execute(
        f"""
        SELECT ae.atividade_id, e.id, e.nome, e.cor
        FROM atividade_etiqueta ae JOIN etiqueta e ON e.id = ae.etiqueta_id
        WHERE ae.atividade_id IN ({marcas})
        ORDER BY e.nome COLLATE NOCASE, e.id
        """,
        list(por_id),
    ).fetchall()
    for atividade_id, *etiqueta in linhas:
        por_id[atividade_id].marcas.append(Etiqueta(*etiqueta))
    for atividade in atividades:
        atividade.etiquetas = [e.id for e in atividade.marcas]


# Atividades ------------------------------------------------------------------------------


@dataclass
class DadosAtividade:
    """O que se digita no formulário da atividade."""

    titulo: str
    descricao: str = ""
    prazo: date | None = None
    fornecedor_id: int | None = None
    prioridade: int = 0
    etiquetas: list[int] = field(default_factory=list)


@dataclass
class Atividade(DadosAtividade):
    id: int = 0
    coluna_id: int = 0
    posicao: int | None = None
    fornecedor_nome: str = ""
    fornecedor_razao_social: str = ""
    fornecedor_ativo: bool = True
    criado_em: datetime | None = None
    alterado_em: datetime | None = None
    movido_em: datetime | None = None
    arquivado_em: datetime | None = None
    coluna_nome: str = ""
    situacao: str = ""
    marcas: list[Etiqueta] = field(default_factory=list)  # as etiquetas, com nome e cor

    @property
    def nome_da_prioridade(self) -> str:
        return PRIORIDADES.get(self.prioridade, "")

    @property
    def atrasada(self) -> bool:
        return self.situacao == ATRASADA

    @property
    def vence_hoje(self) -> bool:
        return self.situacao == VENCE_HOJE

    @property
    def concluida(self) -> bool:
        return self.situacao == CONCLUIDA

    def combina(self, busca: str) -> bool:
        """RF30: título, descrição, fornecedor e etiquetas, sem diferenciar maiúsculas e
        acentos."""
        if not busca.strip():
            return True
        campos = [self.titulo, self.descricao, self.fornecedor_nome, self.fornecedor_razao_social]
        campos += [e.nome for e in self.marcas]
        return any(encontrar(campo, busca) for campo in campos)

    def dados(self) -> DadosAtividade:
        return DadosAtividade(
            self.titulo,
            self.descricao,
            self.prazo,
            self.fornecedor_id,
            self.prioridade,
            [e.id for e in self.marcas],
        )


@dataclass
class ColunaDoQuadro:
    coluna: Coluna
    atividades: list[Atividade]


_SELECAO = """
    SELECT a.id, a.titulo, a.descricao, a.prazo, f.id, a.coluna_id, a.posicao,
        coalesce(nullif(f.nome_fantasia, ''), f.razao_social, ''), coalesce(f.razao_social, ''),
        coalesce(f.ativo, 1), a.criado_em, a.alterado_em, a.movido_em, a.arquivado_em,
        coalesce(c.nome, ''), coalesce(c.conclusao, 0), a.prioridade
    FROM atividade a
    LEFT JOIN fornecedor f ON f.id = a.fornecedor_id
    LEFT JOIN coluna_atividade c ON c.id = a.coluna_id
"""


def _montar(linha: tuple, hoje: date) -> Atividade:
    (
        atividade_id,
        titulo,
        descricao,
        prazo,
        fornecedor_id,
        coluna_id,
        posicao,
        fornecedor_nome,
        razao_social,
        fornecedor_ativo,
        criado_em,
        alterado_em,
        movido_em,
        arquivado_em,
        coluna_nome,
        conclusao,
        prioridade,
    ) = linha
    prazo = date.fromisoformat(prazo) if prazo else None
    return Atividade(
        titulo,
        descricao,
        prazo,
        fornecedor_id,
        prioridade,
        id=atividade_id,
        coluna_id=coluna_id,
        posicao=posicao,
        fornecedor_nome=fornecedor_nome,
        fornecedor_razao_social=razao_social,
        fornecedor_ativo=bool(fornecedor_ativo),
        criado_em=_data(criado_em),
        alterado_em=_data(alterado_em),
        movido_em=_data(movido_em),
        arquivado_em=_data(arquivado_em),
        coluna_nome=coluna_nome,
        situacao=situacao_do_prazo(prazo, hoje, bool(conclusao)),
    )


def obter_quadro(conexao: sqlite3.Connection, hoje: date | None = None) -> list[ColunaDoQuadro]:
    """As colunas em ordem, cada uma com as atividades ativas na ordem do quadro."""
    hoje = hoje or date.today()
    quadro = [ColunaDoQuadro(coluna, []) for coluna in listar_colunas(conexao)]
    por_id = {item.coluna.id: item for item in quadro}
    linhas = conexao.execute(
        _SELECAO + " WHERE a.arquivado_em IS NULL ORDER BY a.coluna_id, a.posicao"
    ).fetchall()
    atividades = [_montar(linha, hoje) for linha in linhas]
    _etiquetas_das_atividades(conexao, atividades)
    for atividade in atividades:
        if atividade.coluna_id in por_id:
            por_id[atividade.coluna_id].atividades.append(atividade)
    return quadro


def obter_atividade(
    conexao: sqlite3.Connection, atividade_id: int, hoje: date | None = None
) -> Atividade:
    linha = conexao.execute(_SELECAO + " WHERE a.id = ?", (atividade_id,)).fetchone()
    if linha is None:
        raise AtividadeInvalida("Atividade não encontrada. Feche a janela e abra o quadro de novo.")
    atividade = _montar(linha, hoje or date.today())
    _etiquetas_das_atividades(conexao, [atividade])
    return atividade


def listar_arquivadas(conexao: sqlite3.Connection, hoje: date | None = None) -> list[Atividade]:
    """As arquivadas mais recentes primeiro."""
    linhas = conexao.execute(
        _SELECAO + " WHERE a.arquivado_em IS NOT NULL ORDER BY a.arquivado_em DESC, a.id DESC"
    ).fetchall()
    atividades = [_montar(linha, hoje or date.today()) for linha in linhas]
    _etiquetas_das_atividades(conexao, atividades)
    return atividades


def problemas_da_atividade(conexao: sqlite3.Connection, dados: DadosAtividade) -> dict[str, str]:
    """Erros por campo, em português. Vazio quando está tudo certo."""
    erros = {}
    if erro := problema_do_titulo(dados.titulo):
        erros["titulo"] = erro
    if (
        dados.fornecedor_id is not None
        and not conexao.execute(
            "SELECT 1 FROM fornecedor WHERE id = ?", (dados.fornecedor_id,)
        ).fetchone()
    ):
        erros["fornecedor"] = "Fornecedor não encontrado. Escolha um fornecedor da lista."
    if dados.prioridade not in PRIORIDADES:
        erros["prioridade"] = "Escolha a prioridade na lista."
    existentes = {e.id for e in listar_etiquetas(conexao)}
    if any(etiqueta not in existentes for etiqueta in dados.etiquetas):
        erros["etiquetas"] = "Uma das etiquetas não existe mais. Feche e abra a atividade de novo."
    return erros


def _validar(conexao: sqlite3.Connection, dados: DadosAtividade) -> tuple:
    erros = problemas_da_atividade(conexao, dados)
    if erros:
        raise AtividadeInvalida(" ".join(erros.values()))
    prazo = dados.prazo.isoformat() if dados.prazo else None
    return (
        dados.titulo.strip(),
        dados.descricao.strip(),
        prazo,
        dados.fornecedor_id,
        dados.prioridade,
    )


def _gravar_etiquetas(conexao: sqlite3.Connection, atividade_id: int, etiquetas: list[int]):
    conexao.execute("DELETE FROM atividade_etiqueta WHERE atividade_id = ?", (atividade_id,))
    conexao.executemany(
        "INSERT INTO atividade_etiqueta (atividade_id, etiqueta_id) VALUES (?, ?)",
        [(atividade_id, etiqueta) for etiqueta in dict.fromkeys(etiquetas)],
    )


def _ordem(conexao: sqlite3.Connection, coluna_id: int) -> list[int]:
    return [
        linha[0]
        for linha in conexao.execute(
            "SELECT id FROM atividade WHERE coluna_id = ? AND arquivado_em IS NULL"
            " ORDER BY posicao, id",
            (coluna_id,),
        )
    ]


def _renumerar(conexao: sqlite3.Connection, ordem: list[int]) -> None:
    for posicao, atividade_id in enumerate(ordem, start=1):
        conexao.execute("UPDATE atividade SET posicao = ? WHERE id = ?", (posicao, atividade_id))


def criar_atividade(conexao: sqlite3.Connection, coluna_id: int, dados: DadosAtividade) -> int:
    """A atividade nova vai para o fim da coluna."""
    valores = _validar(conexao, dados)
    obter_coluna(conexao, coluna_id)
    agora = _agora()
    with conexao:
        posicao = len(_ordem(conexao, coluna_id)) + 1
        cursor = conexao.execute(
            """
            INSERT INTO atividade (titulo, descricao, prazo, fornecedor_id, prioridade,
                coluna_id, posicao, criado_em, alterado_em, movido_em)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (*valores, coluna_id, posicao, agora, agora, agora),
        )
        _gravar_etiquetas(conexao, cursor.lastrowid, dados.etiquetas)
    return cursor.lastrowid


def editar_atividade(conexao: sqlite3.Connection, atividade_id: int, dados: DadosAtividade):
    obter_atividade(conexao, atividade_id)
    valores = _validar(conexao, dados)
    with conexao:
        conexao.execute(
            """
            UPDATE atividade SET titulo = ?, descricao = ?, prazo = ?, fornecedor_id = ?,
                prioridade = ?, alterado_em = ?
            WHERE id = ?
            """,
            (*valores, _agora(), atividade_id),
        )
        _gravar_etiquetas(conexao, atividade_id, dados.etiquetas)


def _registrar_movimento(
    conexao: sqlite3.Connection, atividade_id: int, origem: str, destino: str, quando: str
) -> None:
    conexao.execute(
        "INSERT INTO movimento_atividade (atividade_id, coluna_origem, coluna_destino, movido_em)"
        " VALUES (?, ?, ?, ?)",
        (atividade_id, origem, destino, quando),
    )


def _nome_da_coluna(conexao: sqlite3.Connection, coluna_id: int) -> str:
    linha = conexao.execute(
        "SELECT nome FROM coluna_atividade WHERE id = ?", (coluna_id,)
    ).fetchone()
    return linha[0] if linha else COLUNA_EXCLUIDA


def mover_atividade(
    conexao: sqlite3.Connection, atividade_id: int, coluna_id: int, posicao: int
) -> int:
    """Leva a atividade para a posição pedida da coluna de destino (RN16).

    Posição menor que 1 vira a primeira; maior que o tamanho vira o fim. Ao trocar de
    coluna, guarda quando e de onde para onde. Tudo numa transação. Devolve a posição final.
    """
    with conexao:
        linha = conexao.execute(
            "SELECT coluna_id, arquivado_em FROM atividade WHERE id = ?", (atividade_id,)
        ).fetchone()
        if linha is None:
            raise AtividadeInvalida(
                "Atividade não encontrada. Feche a janela e abra o quadro de novo."
            )
        origem_id, arquivado_em = linha
        if arquivado_em is not None:
            raise AtividadeInvalida("Esta atividade está arquivada. Restaure-a antes de mover.")
        destino = obter_coluna(conexao, coluna_id)
        trocou = origem_id != coluna_id
        ordem = [i for i in _ordem(conexao, origem_id) if i != atividade_id]
        if trocou:
            _renumerar(conexao, ordem)
            ordem = _ordem(conexao, coluna_id)
        posicao = min(max(posicao, 1), len(ordem) + 1)
        ordem.insert(posicao - 1, atividade_id)
        if trocou:
            agora = _agora()
            conexao.execute(
                "UPDATE atividade SET coluna_id = ?, movido_em = ? WHERE id = ?",
                (coluna_id, agora, atividade_id),
            )
            _registrar_movimento(
                conexao, atividade_id, _nome_da_coluna(conexao, origem_id), destino.nome, agora
            )
        _renumerar(conexao, ordem)
    return posicao


def arquivar_atividade(conexao: sqlite3.Connection, atividade_id: int) -> None:
    """Tira do quadro sem apagar; a coluna de origem fica guardada para restaurar (RN17)."""
    atividade = obter_atividade(conexao, atividade_id)
    if atividade.arquivado_em is not None:
        return
    with conexao:
        conexao.execute(
            "UPDATE atividade SET arquivado_em = ?, posicao = NULL WHERE id = ?",
            (_agora(), atividade_id),
        )
        _renumerar(conexao, _ordem(conexao, atividade.coluna_id))


def restaurar_atividade(conexao: sqlite3.Connection, atividade_id: int) -> int:
    """Volta para o fim da coluna de origem; se ela não existir mais, da primeira coluna.
    Devolve a coluna em que a atividade ficou."""
    atividade = obter_atividade(conexao, atividade_id)
    if atividade.arquivado_em is None:
        return atividade.coluna_id
    colunas = listar_colunas(conexao)
    if not colunas:
        raise ColunaInvalida("O quadro não tem colunas. Crie uma coluna antes de restaurar.")
    existe = any(c.id == atividade.coluna_id for c in colunas)
    coluna_id = atividade.coluna_id if existe else colunas[0].id
    agora = _agora()
    with conexao:
        posicao = len(_ordem(conexao, coluna_id)) + 1
        conexao.execute(
            "UPDATE atividade SET arquivado_em = NULL, posicao = ?, coluna_id = ? WHERE id = ?",
            (posicao, coluna_id, atividade_id),
        )
        if not existe:
            conexao.execute(
                "UPDATE atividade SET movido_em = ? WHERE id = ?", (agora, atividade_id)
            )
            _registrar_movimento(conexao, atividade_id, COLUNA_EXCLUIDA, colunas[0].nome, agora)
    return coluna_id


def excluir_atividade(conexao: sqlite3.Connection, atividade_id: int) -> None:
    """RN17: excluir definitivamente só existe para atividade arquivada."""
    atividade = obter_atividade(conexao, atividade_id)
    if atividade.arquivado_em is None:
        raise AtividadeInvalida(
            "Só dá para excluir uma atividade arquivada. Arquive a atividade antes."
        )
    with conexao:
        conexao.execute("DELETE FROM movimento_atividade WHERE atividade_id = ?", (atividade_id,))
        conexao.execute("DELETE FROM atividade_etiqueta WHERE atividade_id = ?", (atividade_id,))
        conexao.execute("DELETE FROM atividade WHERE id = ?", (atividade_id,))
        _renumerar(conexao, _ordem(conexao, atividade.coluna_id))


@dataclass
class Movimento:
    coluna_origem: str
    coluna_destino: str
    movido_em: datetime


def movimentos(conexao: sqlite3.Connection, atividade_id: int) -> list[Movimento]:
    linhas = conexao.execute(
        "SELECT coluna_origem, coluna_destino, movido_em FROM movimento_atividade"
        " WHERE atividade_id = ? ORDER BY movido_em, id",
        (atividade_id,),
    ).fetchall()
    return [Movimento(origem, destino, _data(quando)) for origem, destino, quando in linhas]


def contar_prazos(conexao: sqlite3.Connection, hoje: date | None = None) -> tuple[int, int]:
    """RF31: quantas atividades estão atrasadas e quantas vencem hoje, fora da conclusão."""
    hoje = (hoje or date.today()).isoformat()
    atrasadas, de_hoje = conexao.execute(
        """
        SELECT count(*) FILTER (WHERE a.prazo < ?), count(*) FILTER (WHERE a.prazo = ?)
        FROM atividade a JOIN coluna_atividade c ON c.id = a.coluna_id
        WHERE a.arquivado_em IS NULL AND c.conclusao = 0 AND a.prazo IS NOT NULL
        """,
        (hoje, hoje),
    ).fetchone()
    return atrasadas, de_hoje
