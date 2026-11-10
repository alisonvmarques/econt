"""Conteúdo das impressões: dados para pagamento (I01) e ficha completa (I02)."""

from __future__ import annotations

from datetime import datetime
from html import escape

from econt.dados.consulta import ResultadoConsulta
from econt.dados.entidade import Entidade
from econt.dados.fornecedores import ChavePix, ContaFornecedor, Fornecedor
from econt.interface.impressao import DadosParaPagamento, Paginada, _cabecalho
from econt.interface.tema import CORES

BORDA = CORES["border/input"]
FUNDO_CABECALHO = CORES["bg/surface-alt"]
APOIO = CORES["text/secondary"]
PERIGO = CORES["status/danger"]


def _cabecalho_entidade(entidade: Entidade | None, assunto: str) -> str:
    if entidade is None:
        return _cabecalho(None, None, assunto, False)
    return _cabecalho(
        entidade.razao_social, f"CNPJ {entidade.cnpj_formatado}", assunto, bool(entidade.logo)
    )


def _tabela(colunas: list[str], linhas: list[list[str]], larguras: list[int]) -> str:
    cabeca = "".join(
        f'<th width="{w}%" align="left" style="font-weight: normal; font-size: 7.5pt; '
        f'color: {APOIO}; background: {FUNDO_CABECALHO};">{escape(c)}</th>'
        for c, w in zip(colunas, larguras, strict=True)
    )
    corpo = "".join(
        "<tr>" + "".join(f"<td>{celula}</td>" for celula in linha) + "</tr>" for linha in linhas
    )
    return (
        f'<table width="100%" cellspacing="0" cellpadding="5" border="1" '
        f'style="border-color: {BORDA}; border-collapse: collapse; font-size: 9pt;">'
        f"<tr>{cabeca}</tr>{corpo}</table>"
    )


def html_bloco_pagamento(resultado: ResultadoConsulta, entidade: Entidade | None) -> str:
    """Um bloco da meia folha: fornecedor, contas e chaves ativas e onde estão cadastradas."""
    f = resultado.fornecedor
    linhas = []
    for cadastro in resultado.cadastros:
        if cadastro.sem_cadastro:
            onde = f'<b style="color: {PERIGO};">Nenhuma: não usar para pagar</b>'
        else:
            onde = " · ".join(escape(c.descricao) for c in cadastro.contas_entidade)
        linhas.append([escape(cadastro.item.nome), escape(cadastro.item.dados), onde])
    if linhas:
        tabela = _tabela(
            ["Conta ou chave Pix", "Dados", "Cadastrada nas contas da entidade"],
            linhas,
            [18, 36, 46],
        )
    else:
        tabela = (
            f'<p style="color: {PERIGO};"><b>Nenhuma conta ou chave Pix ativa: '
            "não há dados para pagamento.</b></p>"
        )
    fantasia = (
        f" · Nome fantasia: {escape(f.nome_fantasia)}" if f.tipo == "pj" and f.nome_fantasia else ""
    )
    return f"""
    <html><body style="font-size: 9pt; color: {CORES["text/primary"]};">
    {_cabecalho_entidade(entidade, "Dados para pagamento")}
    <p style="font-size: 14pt; font-weight: 600; margin-top: 12px; margin-bottom: 2px;">
      {escape(f.razao_social)}</p>
    <p style="color: {APOIO}; margin-top: 0;">
      {f.nome_do_documento} {escape(f.documento_formatado)}{fantasia}</p>
    {tabela}
    </body></html>"""


def dados_para_pagamento(
    resultados: list[ResultadoConsulta],
    entidade: Entidade | None,
    quando: datetime | None = None,
) -> DadosParaPagamento:
    blocos = [html_bloco_pagamento(r, entidade) for r in resultados]
    return DadosParaPagamento(blocos, entidade.logo if entidade else None, quando or datetime.now())


def _data(iso: str) -> str:
    return datetime.fromisoformat(iso).strftime("%d/%m/%Y") if iso else "—"


def ficha_completa(
    fornecedor: Fornecedor,
    contas: list[ContaFornecedor],
    chaves: list[ChavePix],
    entidade: Entidade | None,
    quando: datetime | None = None,
) -> Paginada:
    """I02 · Todos os dados, todas as contas e chaves (ativas e inativas) e observações."""
    f = fornecedor
    dados = [
        (f.nome_do_documento, f.documento_formatado),
        ("Tipo", f.nome_do_tipo),
    ]
    if f.tipo == "pj":
        dados.append(("Nome fantasia", f.nome_fantasia or "—"))
    dados += [
        ("Situação", "Ativo" if f.ativo else "Inativo"),
        ("Telefone", f.telefone or "—"),
        ("E-mail", f.email or "—"),
        ("Endereço", f.endereco or "—"),
        ("Observações", f.observacoes or "—"),
        (
            "Cadastro",
            f"Criado em {_data(f.criado_em)} · última alteração em {_data(f.alterado_em)}",
        ),
    ]
    linhas_dados = "".join(
        f'<tr><td width="24%" style="font-size: 7.5pt; color: {APOIO};">{escape(r)}</td>'
        f"<td>{escape(v)}</td></tr>"
        for r, v in dados
    )
    contas_html = (
        _tabela(
            ["Banco", "Agência", "Conta", "Tipo", "Situação"],
            [
                [
                    escape(c.banco_rotulo),
                    escape(c.agencia),
                    escape(c.conta),
                    escape(c.nome_do_tipo),
                    "Ativa" if c.ativa else "Inativa",
                ]
                for c in contas
            ],
            [36, 14, 20, 16, 14],
        )
        if contas
        else f'<p style="color: {APOIO};">Nenhuma conta bancária cadastrada.</p>'
    )
    chaves_html = (
        _tabela(
            ["Tipo", "Chave", "Situação"],
            [
                [
                    escape(c.nome_do_tipo),
                    escape(c.chave_formatada),
                    "Ativa" if c.ativa else "Inativa",
                ]
                for c in chaves
            ],
            [18, 66, 16],
        )
        if chaves
        else f'<p style="color: {APOIO};">Nenhuma chave Pix cadastrada.</p>'
    )
    html = f"""
    <html><body style="font-size: 9.5pt; color: {CORES["text/primary"]};">
    {_cabecalho_entidade(entidade, "Ficha do fornecedor")}
    <p style="font-size: 14pt; font-weight: 600; margin-top: 12px;">{escape(f.razao_social)}</p>
    <table width="100%" cellpadding="4">{linhas_dados}</table>
    <p style="font-size: 11pt; font-weight: 600; margin-top: 14px;">Contas bancárias</p>
    {contas_html}
    <p style="font-size: 11pt; font-weight: 600; margin-top: 14px;">Chaves Pix</p>
    {chaves_html}
    </body></html>"""
    quando = quando or datetime.now()
    nome = f"ficha-{f.documento}-{quando:%Y%m%d}.pdf"
    return Paginada(html, entidade.logo if entidade else None, quando, "Ficha do fornecedor", nome)
