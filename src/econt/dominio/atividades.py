"""Regras das atividades do quadro: título, prazo, prioridade, etiquetas e onde o cartão cai
ao soltar (RN14 a RN16, RN19).

Atividade na coluna de conclusão conta como concluída e nunca fica atrasada (RN15).
"""

from __future__ import annotations

import re
from datetime import date

from econt.dominio.texto import normalizar

TAMANHO_DO_TITULO = 120
TAMANHO_DO_NOME_DA_COLUNA = 40
TAMANHO_DO_NOME_DA_ETIQUETA = 30

# Prioridade (RF33): 0 é sem prioridade.
PRIORIDADES = {0: "Sem prioridade", 1: "Baixa", 2: "Média", 3: "Alta"}

# Cores das etiquetas (RF32), com os papéis de etiqueta do tema.
CORES_DE_ETIQUETA = {
    "neutra": "Cinza",
    "info": "Azul",
    "sucesso": "Verde",
    "atencao": "Amarelo",
    "perigo": "Vermelho",
}

# Situação do prazo de uma atividade, na ordem em que pedem atenção.
ATRASADA = "atrasada"
VENCE_HOJE = "hoje"
NO_PRAZO = "no_prazo"
SEM_PRAZO = "sem_prazo"
CONCLUIDA = "concluida"

_DATA = re.compile(r"(\d{1,2})/(\d{1,2})/(\d{4})")


class AtividadeInvalida(ValueError):
    pass


def problema_do_titulo(titulo: str) -> str | None:
    titulo = titulo.strip()
    if not titulo:
        return "Informe o título, como Conferir notas de outubro."
    if len(titulo) > TAMANHO_DO_TITULO:
        return (
            f"Use até {TAMANHO_DO_TITULO} caracteres no título (agora são {len(titulo)}). "
            "Os detalhes vão na descrição."
        )
    return None


def _problema_do_nome(
    nome: str, outros: list[str], coisa: str, tamanho: int, exemplo: str
) -> str | None:
    nome = nome.strip()
    if not nome:
        return f"Informe o nome da {coisa}, como {exemplo}."
    if len(nome) > tamanho:
        return f"Use até {tamanho} caracteres no nome da {coisa}."
    if any(normalizar(nome) == normalizar(outro.strip()) for outro in outros):
        return f"Já existe uma {coisa} chamada {nome}. Escolha outro nome."
    return None


def problema_do_nome_da_coluna(nome: str, outros: list[str]) -> str | None:
    """RN14: nome obrigatório e sem repetir, sem diferenciar maiúsculas e acentos."""
    return _problema_do_nome(nome, outros, "coluna", TAMANHO_DO_NOME_DA_COLUNA, "Aguardando")


def problema_do_nome_da_etiqueta(nome: str, outros: list[str]) -> str | None:
    """RN19: a mesma regra das colunas, com nomes mais curtos."""
    return _problema_do_nome(nome, outros, "etiqueta", TAMANHO_DO_NOME_DA_ETIQUETA, "Banco")


def ler_prazo(texto: str) -> date | None:
    """Data no formato brasileiro (dd/mm/aaaa). Em branco, a atividade fica sem prazo."""
    texto = texto.strip()
    if not texto:
        return None
    partes = _DATA.fullmatch(texto)
    erro = "Informe o prazo assim: 25/11/2026, ou deixe em branco."
    if partes is None:
        raise AtividadeInvalida(erro)
    dia, mes, ano = (int(p) for p in partes.groups())
    try:
        return date(ano, mes, dia)
    except ValueError:
        raise AtividadeInvalida(f"Esta data não existe. {erro}") from None


def formatar_prazo(prazo: date | None) -> str:
    return prazo.strftime("%d/%m/%Y") if prazo else ""


def situacao_do_prazo(prazo: date | None, hoje: date, concluida: bool = False) -> str:
    if concluida:
        return CONCLUIDA
    if prazo is None:
        return SEM_PRAZO
    if prazo < hoje:
        return ATRASADA
    if prazo == hoje:
        return VENCE_HOJE
    return NO_PRAZO


def posicao_ao_soltar(ordem: list[int], atividade_id: int, antes_de: int | None) -> int:
    """Posição final (a partir de 1) de quem é solto antes de `antes_de` numa coluna.

    `ordem` é a ordem real da coluna de destino. Com `antes_de` vazio, vai para o fim. Como
    a conta usa a ordem real, a busca pode esconder cartões sem mudar onde o cartão cai.
    """
    if antes_de == atividade_id and atividade_id in ordem:
        return ordem.index(atividade_id) + 1  # solto em cima de si mesmo: fica onde está
    restantes = [i for i in ordem if i != atividade_id]
    if antes_de is None or antes_de not in restantes:
        return len(restantes) + 1
    return restantes.index(antes_de) + 1
