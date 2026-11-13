"""Quadro de atividades: migração, colunas, atividades, posições e prazos (RF27 a RF31)."""

import sqlite3
from datetime import date

import pytest

from econt.dados import atividades as dados_atividades
from econt.dados.atividades import (
    ColunaInvalida,
    DadosAtividade,
    arquivar_atividade,
    contar_prazos,
    criar_atividade,
    criar_coluna,
    definir_conclusao,
    editar_atividade,
    excluir_atividade,
    excluir_coluna,
    listar_arquivadas,
    listar_colunas,
    mover_atividade,
    mover_coluna,
    movimentos,
    obter_atividade,
    obter_quadro,
    renomear_coluna,
    restaurar_atividade,
)
from econt.dados.backup import fazer_backup, restaurar
from econt.dados.banco import MIGRACOES, BaseDeDados
from econt.dados.fornecedores import (
    DadosFornecedor,
    cadastrar_fornecedor,
    definir_fornecedor_ativo,
    excluir_fornecedor,
)
from econt.dados.painel import resumir
from econt.dominio.atividades import (
    ATRASADA,
    CONCLUIDA,
    NO_PRAZO,
    SEM_PRAZO,
    VENCE_HOJE,
    AtividadeInvalida,
    formatar_prazo,
    ler_prazo,
    posicao_ao_soltar,
    problema_do_titulo,
    situacao_do_prazo,
)

SENHA = "fundo2026saude"
HOJE = date(2026, 11, 13)
A_FAZER, EM_ANDAMENTO, CONCLUIDO = 1, 2, 3


@pytest.fixture
def base(tmp_path):
    return BaseDeDados.criar(tmp_path / "dados.econt", SENHA)[0]


@pytest.fixture
def c(base):
    return base.conexao


def _criar(c, coluna, *titulos, **campos) -> list[int]:
    return [criar_atividade(c, coluna, DadosAtividade(t, **campos)) for t in titulos]


def _titulos(c, coluna_id) -> list[str]:
    quadro = {item.coluna.id: item for item in obter_quadro(c, HOJE)}
    return [a.titulo for a in quadro[coluna_id].atividades]


def _posicoes(c) -> dict[int, list[int]]:
    return {item.coluna.id: [a.posicao for a in item.atividades] for item in obter_quadro(c, HOJE)}


def _sem_buracos(c) -> None:
    for coluna, posicoes in _posicoes(c).items():
        assert posicoes == list(range(1, len(posicoes) + 1)), coluna


# Migração --------------------------------------------------------------------------------


def _estrutura(conexao) -> list[tuple]:
    return conexao.execute(
        "SELECT type, name, sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%' ORDER BY name"
    ).fetchall()


def test_base_nova_nasce_com_as_tres_colunas(c):
    colunas = listar_colunas(c)
    assert [(k.nome, k.posicao, k.conclusao) for k in colunas] == [
        ("A fazer", 1, False),
        ("Em andamento", 2, False),
        ("Concluído", 3, True),
    ]
    assert obter_quadro(c) and all(not item.atividades for item in obter_quadro(c))


def test_base_da_versao_anterior_ganha_o_quadro_sem_perder_nada(tmp_path, monkeypatch, base):
    caminho = tmp_path / "antiga.econt"
    monkeypatch.setattr("econt.dados.banco.MIGRACOES", MIGRACOES[:6])
    antiga = BaseDeDados.criar(caminho, SENHA)[0]
    assert antiga.versao() == 6
    cadastrar_fornecedor(
        antiga.conexao, DadosFornecedor("pj", "11.222.333/0001-81", "Distribuidora Exemplo")
    )
    antiga.fechar()
    monkeypatch.undo()

    aberta = BaseDeDados.abrir(caminho, senha=SENHA)
    assert aberta.versao() == len(MIGRACOES)
    assert _estrutura(aberta.conexao) == _estrutura(base.conexao)
    assert [k.nome for k in listar_colunas(aberta.conexao)] == [
        "A fazer",
        "Em andamento",
        "Concluído",
    ]
    nome = aberta.conexao.execute("SELECT razao_social FROM fornecedor").fetchone()[0]
    assert nome == "Distribuidora Exemplo"


def test_quadro_sobrevive_a_fechar_e_ao_backup(tmp_path, base):
    caminho = tmp_path / "dados.econt"
    a, b = _criar(base.conexao, A_FAZER, "Conferir notas", "Pagar energia")
    mover_atividade(base.conexao, b, EM_ANDAMENTO, 1)
    base.salvar()
    copia = fazer_backup(caminho, tmp_path / "backups")
    arquivar_atividade(base.conexao, a)
    base.fechar()

    aberta = restaurar(copia, caminho, senha=SENHA)
    assert _titulos(aberta.conexao, A_FAZER) == ["Conferir notas"]
    assert _titulos(aberta.conexao, EM_ANDAMENTO) == ["Pagar energia"]


# Colunas ---------------------------------------------------------------------------------


def test_nome_da_coluna_obrigatorio_e_sem_repetir(c):
    with pytest.raises(ColunaInvalida, match="Informe o nome"):
        criar_coluna(c, "   ")
    with pytest.raises(ColunaInvalida, match="Já existe uma coluna chamada concluido"):
        criar_coluna(c, "concluido")
    with pytest.raises(ColunaInvalida, match="Já existe"):
        renomear_coluna(c, A_FAZER, "EM ANDAMENTO")
    renomear_coluna(c, A_FAZER, "A Fazer")  # a própria coluna pode mudar só a caixa
    nova = criar_coluna(c, "  Aguardando banco ")
    assert [k.nome for k in listar_colunas(c)][-1] == "Aguardando banco"
    assert listar_colunas(c)[-1].id == nova


def test_mover_coluna_renumera(c):
    nova = criar_coluna(c, "Aguardando")
    mover_coluna(c, nova, 1)
    assert [k.nome for k in listar_colunas(c)] == [
        "Aguardando",
        "A fazer",
        "Em andamento",
        "Concluído",
    ]
    mover_coluna(c, nova, 99)
    assert [k.posicao for k in listar_colunas(c)] == [1, 2, 3, 4]
    assert listar_colunas(c)[-1].id == nova


def test_nao_exclui_coluna_com_atividades_nem_a_ultima(c):
    (a,) = _criar(c, EM_ANDAMENTO, "Conferir notas")
    with pytest.raises(ColunaInvalida, match="Mova ou exclua as atividades"):
        excluir_coluna(c, EM_ANDAMENTO)
    arquivar_atividade(c, a)
    with pytest.raises(ColunaInvalida, match="1 arquivada"):
        excluir_coluna(c, EM_ANDAMENTO)
    excluir_atividade(c, a)
    excluir_coluna(c, EM_ANDAMENTO)
    assert [(k.nome, k.posicao) for k in listar_colunas(c)] == [("A fazer", 1), ("Concluído", 2)]
    excluir_coluna(c, CONCLUIDO)
    with pytest.raises(ColunaInvalida, match="pelo menos uma coluna"):
        excluir_coluna(c, A_FAZER)


def test_uma_unica_coluna_de_conclusao(c):
    definir_conclusao(c, A_FAZER, True)
    assert [k.nome for k in listar_colunas(c) if k.conclusao] == ["A fazer"]
    nova = criar_coluna(c, "Pago", conclusao=True)
    assert [k.id for k in listar_colunas(c) if k.conclusao] == [nova]
    definir_conclusao(c, nova, False)
    assert not any(k.conclusao for k in listar_colunas(c))
    with pytest.raises(sqlite3.IntegrityError):
        c.execute("UPDATE coluna_atividade SET conclusao = 1")


# Atividades ------------------------------------------------------------------------------


def test_criar_vai_para_o_fim_da_coluna(c):
    _criar(c, A_FAZER, "Primeira", "Segunda", "Terceira")
    assert _titulos(c, A_FAZER) == ["Primeira", "Segunda", "Terceira"]
    assert _posicoes(c)[A_FAZER] == [1, 2, 3]


def test_titulo_obrigatorio_e_ate_120_caracteres(c):
    with pytest.raises(AtividadeInvalida, match="Informe o título"):
        criar_atividade(c, A_FAZER, DadosAtividade("  "))
    with pytest.raises(AtividadeInvalida, match="até 120 caracteres"):
        criar_atividade(c, A_FAZER, DadosAtividade("x" * 121))
    criar_atividade(c, A_FAZER, DadosAtividade("x" * 120))
    with pytest.raises(ColunaInvalida):
        criar_atividade(c, 99, DadosAtividade("Sem coluna"))


def test_editar_guarda_os_campos(c):
    (a,) = _criar(c, A_FAZER, "Conferir notas")
    f = cadastrar_fornecedor(c, DadosFornecedor("pj", "11.222.333/0001-81", "Distribuidora"))
    editar_atividade(
        c, a, DadosAtividade(" Conferir notas de outubro ", "Linha 1\nLinha 2", HOJE, f)
    )
    atividade = obter_atividade(c, a, HOJE)
    assert atividade.titulo == "Conferir notas de outubro"
    assert atividade.descricao == "Linha 1\nLinha 2"
    assert atividade.prazo == HOJE
    assert atividade.fornecedor_nome == "Distribuidora"
    assert atividade.alterado_em >= atividade.criado_em
    with pytest.raises(AtividadeInvalida, match="Fornecedor não encontrado"):
        editar_atividade(c, a, DadosAtividade("Título", fornecedor_id=999))


def test_mover_dentro_da_coluna(c):
    a, b, d, e = _criar(c, A_FAZER, "A", "B", "D", "E")
    mover_atividade(c, d, A_FAZER, 2)  # para cima
    assert _titulos(c, A_FAZER) == ["A", "D", "B", "E"]
    mover_atividade(c, a, A_FAZER, 3)  # para baixo
    assert _titulos(c, A_FAZER) == ["D", "B", "A", "E"]
    mover_atividade(c, e, A_FAZER, 1)  # primeira
    assert _titulos(c, A_FAZER) == ["E", "D", "B", "A"]
    mover_atividade(c, e, A_FAZER, 4)  # última
    assert _titulos(c, A_FAZER) == ["D", "B", "A", "E"]
    _sem_buracos(c)
    assert movimentos(c, e) == []


def test_mover_entre_colunas_em_posicao_especifica(c):
    a, b = _criar(c, A_FAZER, "A", "B")
    _criar(c, EM_ANDAMENTO, "X", "Y", "Z")
    assert mover_atividade(c, a, EM_ANDAMENTO, 2) == 2
    assert _titulos(c, A_FAZER) == ["B"]
    assert _titulos(c, EM_ANDAMENTO) == ["X", "A", "Y", "Z"]
    _sem_buracos(c)
    (movimento,) = movimentos(c, a)
    assert (movimento.coluna_origem, movimento.coluna_destino) == ("A fazer", "Em andamento")
    assert obter_atividade(c, a).movido_em == movimento.movido_em


def test_posicao_fora_do_intervalo(c):
    a, b = _criar(c, A_FAZER, "A", "B")
    _criar(c, EM_ANDAMENTO, "X")
    assert mover_atividade(c, b, A_FAZER, 0) == 1
    assert _titulos(c, A_FAZER) == ["B", "A"]
    assert mover_atividade(c, b, A_FAZER, -5) == 1
    assert mover_atividade(c, b, EM_ANDAMENTO, 50) == 2
    assert _titulos(c, EM_ANDAMENTO) == ["X", "B"]
    _sem_buracos(c)


def test_historico_guarda_o_nome_mesmo_depois_de_renomear(c):
    (a,) = _criar(c, A_FAZER, "A")
    mover_atividade(c, a, EM_ANDAMENTO, 1)
    mover_atividade(c, a, EM_ANDAMENTO, 1)  # mesma coluna: não registra
    renomear_coluna(c, EM_ANDAMENTO, "Fazendo")
    mover_atividade(c, a, CONCLUIDO, 1)
    assert [(m.coluna_origem, m.coluna_destino) for m in movimentos(c, a)] == [
        ("A fazer", "Em andamento"),
        ("Fazendo", "Concluído"),
    ]


def test_mover_desfaz_tudo_se_algo_falhar(c, monkeypatch):
    a, b = _criar(c, A_FAZER, "A", "B")
    _criar(c, EM_ANDAMENTO, "X")
    antes = _posicoes(c)

    def falhar(*args):
        raise sqlite3.OperationalError("disco cheio")

    monkeypatch.setattr(dados_atividades, "_registrar_movimento", falhar)
    with pytest.raises(sqlite3.OperationalError):
        mover_atividade(c, a, EM_ANDAMENTO, 1)
    assert _posicoes(c) == antes
    assert _titulos(c, A_FAZER) == ["A", "B"]
    assert obter_atividade(c, a).coluna_id == A_FAZER


def test_mover_valida_atividade_e_coluna(c):
    (a,) = _criar(c, A_FAZER, "A")
    with pytest.raises(ColunaInvalida):
        mover_atividade(c, a, 99, 1)
    with pytest.raises(AtividadeInvalida, match="não encontrada"):
        mover_atividade(c, 99, A_FAZER, 1)
    arquivar_atividade(c, a)
    with pytest.raises(AtividadeInvalida, match="arquivada"):
        mover_atividade(c, a, EM_ANDAMENTO, 1)


def test_arquivar_restaurar_e_excluir_mantem_a_sequencia(c):
    a, b, d = _criar(c, A_FAZER, "A", "B", "D")
    arquivar_atividade(c, b)
    assert _titulos(c, A_FAZER) == ["A", "D"]
    _sem_buracos(c)
    assert [x.titulo for x in listar_arquivadas(c)] == ["B"]
    assert restaurar_atividade(c, b) == A_FAZER
    assert _titulos(c, A_FAZER) == ["A", "D", "B"]  # volta para o fim da coluna de origem
    _sem_buracos(c)
    with pytest.raises(AtividadeInvalida, match="Só dá para excluir uma atividade arquivada"):
        excluir_atividade(c, a)
    arquivar_atividade(c, a)
    mover_atividade(c, d, EM_ANDAMENTO, 1)
    excluir_atividade(c, a)
    assert listar_arquivadas(c) == []
    _sem_buracos(c)
    with pytest.raises(AtividadeInvalida):
        obter_atividade(c, a)


def test_restaurar_sem_a_coluna_de_origem_vai_para_a_primeira(c):
    (a,) = _criar(c, EM_ANDAMENTO, "A")
    arquivar_atividade(c, a)
    # Uma base gravada com a coluna já apagada (a regra de exclusão não deixa pelo ECont).
    c.execute("DELETE FROM coluna_atividade WHERE id = ?", (EM_ANDAMENTO,))
    assert restaurar_atividade(c, a) == A_FAZER
    assert _titulos(c, A_FAZER) == ["A"]
    assert movimentos(c, a)[-1].coluna_destino == "A fazer"


# Prazo -----------------------------------------------------------------------------------


def test_situacao_do_prazo():
    assert situacao_do_prazo(date(2026, 11, 12), HOJE) == ATRASADA
    assert situacao_do_prazo(HOJE, HOJE) == VENCE_HOJE
    assert situacao_do_prazo(date(2026, 11, 14), HOJE) == NO_PRAZO
    assert situacao_do_prazo(None, HOJE) == SEM_PRAZO
    assert situacao_do_prazo(date(2026, 1, 1), HOJE, concluida=True) == CONCLUIDA


def test_ler_e_formatar_prazo():
    assert ler_prazo("") is None
    assert ler_prazo(" 5/1/2027 ") == date(2027, 1, 5)
    assert formatar_prazo(date(2027, 1, 5)) == "05/01/2027"
    with pytest.raises(AtividadeInvalida, match="assim: 25/11/2026"):
        ler_prazo("2027-01-05")
    with pytest.raises(AtividadeInvalida, match="não existe"):
        ler_prazo("31/02/2027")


def test_titulo_com_espacos_conta_o_texto():
    assert problema_do_titulo("  Conferir  ") is None


def test_prazo_no_quadro_e_contagem(c):
    ontem, amanha = date(2026, 11, 12), date(2026, 11, 14)
    a, b, _, _ = (
        criar_atividade(c, A_FAZER, DadosAtividade("Atrasada", prazo=ontem)),
        criar_atividade(c, A_FAZER, DadosAtividade("Hoje", prazo=HOJE)),
        criar_atividade(c, A_FAZER, DadosAtividade("Amanhã", prazo=amanha)),
        criar_atividade(c, A_FAZER, DadosAtividade("Sem prazo")),
    )
    situacoes = {x.titulo: x.situacao for x in obter_quadro(c, HOJE)[0].atividades}
    assert situacoes == {
        "Atrasada": ATRASADA,
        "Hoje": VENCE_HOJE,
        "Amanhã": NO_PRAZO,
        "Sem prazo": SEM_PRAZO,
    }
    assert contar_prazos(c, HOJE) == (1, 1)
    mover_atividade(c, a, CONCLUIDO, 1)
    assert obter_atividade(c, a, HOJE).situacao == CONCLUIDA
    assert contar_prazos(c, HOJE) == (0, 1)
    arquivar_atividade(c, b)
    assert contar_prazos(c, HOJE) == (0, 0)


def test_resumo_do_inicio_conta_atrasadas_e_de_hoje(c):
    from datetime import datetime

    criar_atividade(c, A_FAZER, DadosAtividade("Atrasada", prazo=date(2026, 11, 1)))
    criar_atividade(c, EM_ANDAMENTO, DadosAtividade("Hoje", prazo=HOJE))
    resumo = resumir(c, datetime(2026, 11, 13, 9, 0))
    assert (resumo.atividades_atrasadas, resumo.atividades_de_hoje) == (1, 1)


# Fornecedor ------------------------------------------------------------------------------


def test_fornecedor_inativo_continua_e_excluido_perde_o_vinculo(c):
    f = cadastrar_fornecedor(
        c,
        DadosFornecedor(
            "pj", "11.222.333/0001-81", "Distribuidora Exemplo Ltda", nome_fantasia="Exemplo"
        ),
    )
    (sem,) = _criar(c, A_FAZER, "Sem fornecedor")
    (a,) = _criar(c, A_FAZER, "Pedir certidão", fornecedor_id=f)
    assert obter_atividade(c, sem).fornecedor_id is None
    definir_fornecedor_ativo(c, f, False)
    atividade = obter_atividade(c, a)
    assert (atividade.fornecedor_nome, atividade.fornecedor_ativo) == ("Exemplo", False)
    assert atividade.combina("distribuidora") and atividade.combina("EXEMPLO")
    excluir_fornecedor(c, f)
    atividade = obter_atividade(c, a)
    assert atividade.fornecedor_id is None and atividade.fornecedor_nome == ""
    assert _titulos(c, A_FAZER) == ["Sem fornecedor", "Pedir certidão"]


def test_busca_por_titulo_descricao_e_fornecedor(c):
    f = cadastrar_fornecedor(c, DadosFornecedor("pf", "529.982.247-25", "Maria Exemplo"))
    criar_atividade(c, A_FAZER, DadosAtividade("Conferir notas", "Notas de saúde"))
    criar_atividade(c, A_FAZER, DadosAtividade("Pagar", fornecedor_id=f))
    atividades = obter_quadro(c)[0].atividades
    assert [a.titulo for a in atividades if a.combina("SAUDE")] == ["Conferir notas"]
    assert [a.titulo for a in atividades if a.combina("maria")] == ["Pagar"]
    assert [a.titulo for a in atividades if a.combina("conf")] == ["Conferir notas"]
    assert len([a for a in atividades if a.combina("  ")]) == 2


# Onde o cartão cai ao soltar ---------------------------------------------------------------


def test_posicao_ao_soltar_usa_a_ordem_real():
    ordem = [10, 20, 30, 40]
    assert posicao_ao_soltar(ordem, 99, 10) == 1  # de outra coluna, antes do primeiro
    assert posicao_ao_soltar(ordem, 99, None) == 5  # no fim
    assert posicao_ao_soltar(ordem, 10, 40) == 3  # descendo na mesma coluna
    assert posicao_ao_soltar(ordem, 40, 20) == 2  # subindo na mesma coluna
    assert posicao_ao_soltar(ordem, 20, 20) == 2  # solto em cima de si mesmo
    # Com a busca escondendo 20 e 30, soltar antes de 40 continua sendo antes de 40.
    assert posicao_ao_soltar(ordem, 99, 40) == 4
