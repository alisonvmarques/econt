from datetime import datetime

import pytest
from PySide6.QtPdf import QPdfDocument

from baliza.dados.banco import BaseDeDados
from baliza.dados.consulta import consultar
from baliza.dados.contas import DadosConta, cadastrar_conta
from baliza.dados.entidade import Entidade, obter_entidade, salvar_entidade
from baliza.dados.fornecedores import (
    DadosContaFornecedor,
    DadosFornecedor,
    cadastrar_fornecedor,
    definir_item_ativo,
    listar_chaves,
    listar_contas_fornecedor,
    obter_fornecedor,
    salvar_chave_pix,
    salvar_conta_fornecedor,
)
from baliza.dados.marcacoes import itens_do_fornecedor, marcar_todas
from baliza.interface.impressao import JanelaImpressao, salvar_pdf_impressao
from baliza.interface.impressoes import dados_para_pagamento, ficha_completa

SENHA = "fundo2026saude"
QUANDO = datetime(2026, 11, 8, 19, 5)


@pytest.fixture
def cenario(tmp_path):
    base = BaseDeDados.criar(tmp_path / "dados.baliza", SENHA)[0]
    c = base.conexao
    salvar_entidade(c, Entidade("Fundo de Saúde Exemplo", "11.222.333/0001-81"))
    cadastrar_conta(c, DadosConta("Conta Movimento", "001", "1234-5", "55555-0"))
    a = cadastrar_fornecedor(
        c, DadosFornecedor("pj", "11.222.333/0001-81", "Distribuidora Exemplo de Materiais Ltda")
    )
    salvar_conta_fornecedor(c, a, DadosContaFornecedor("001", "1234-5", "98765-4"))
    salvar_conta_fornecedor(c, a, DadosContaFornecedor("237", "0101", "33333-1"))
    salvar_chave_pix(c, a, "email", "financeiro@exemplo.com.br")
    conta, inativa, _ = itens_do_fornecedor(c, a)
    marcar_todas(c, conta)
    definir_item_ativo(c, "conta_fornecedor", inativa.id, False)
    b = cadastrar_fornecedor(c, DadosFornecedor("pf", "529.982.247-25", "Maria Exemplo da Silva"))
    salvar_chave_pix(c, b, "cpf", "529.982.247-25")
    return base, a, b


def _esqueleto(texto: str) -> str:
    """Só letras e números: a extração de texto do PDF troca alguns sinais (hífen, dois-pontos)
    por caracteres internos da fonte, embora eles apareçam normais na folha."""
    return "".join(c for c in texto if c.isalnum())


def _texto_do_pdf(caminho) -> tuple[int, str]:
    pdf = QPdfDocument(None)
    pdf.load(str(caminho))
    paginas = pdf.pageCount()
    texto = "\n".join(pdf.getAllText(i).text() for i in range(paginas))
    pdf.close()
    return paginas, _esqueleto(texto)


def test_folha_completa_com_dois_fornecedores_e_linha_de_corte(aplicacao, cenario, tmp_path):
    base, a, b = cenario
    c = base.conexao
    impressao = dados_para_pagamento([consultar(c, a), consultar(c, b)], obter_entidade(c), QUANDO)
    salvar_pdf_impressao(impressao, str(tmp_path / "folha.pdf"))
    paginas, texto = _texto_do_pdf(tmp_path / "folha.pdf")
    assert paginas == 1
    assert _esqueleto("Distribuidora Exemplo de Materiais Ltda") in texto
    assert _esqueleto("Maria Exemplo da Silva") in texto
    assert _esqueleto("corte aqui") in texto
    assert texto.count(_esqueleto("Emitido pelo Baliza em 08/11/2026 às 19:05")) == 2
    assert _esqueleto("Fundo de Saúde Exemplo") in texto


def test_meia_folha_mostra_onde_esta_cadastrada_e_so_o_que_esta_ativo(aplicacao, cenario, tmp_path):
    base, a, _ = cenario
    c = base.conexao
    salvar_pdf_impressao(
        dados_para_pagamento([consultar(c, a)], obter_entidade(c), QUANDO),
        str(tmp_path / "meia.pdf"),
    )
    _, texto = _texto_do_pdf(tmp_path / "meia.pdf")
    assert _esqueleto("001 · Ag. 1234-5 · C/C 98765-4") in texto
    assert _esqueleto("Conta Movimento") in texto
    assert _esqueleto("Nenhuma: não usar para pagar") in texto
    assert _esqueleto("33333-1") not in texto  # conta inativa não sai na meia folha (RNF11)


def test_meia_folha_aceita_um_ou_dois(aplicacao, cenario):
    base, a, b = cenario
    resultados = [consultar(base.conexao, a)] * 3
    with pytest.raises(ValueError):
        dados_para_pagamento(resultados, None, QUANDO)


def test_ficha_completa_quebra_pagina_e_numera(aplicacao, cenario, tmp_path):
    base, a, _ = cenario
    c = base.conexao
    for numero in range(60):
        salvar_conta_fornecedor(c, a, DadosContaFornecedor("104", "0456", f"{numero + 100}-1"))
    impressao = ficha_completa(
        obter_fornecedor(c, a),
        listar_contas_fornecedor(c, a),
        listar_chaves(c, a),
        obter_entidade(c),
        QUANDO,
    )
    salvar_pdf_impressao(impressao, str(tmp_path / "ficha.pdf"))
    paginas, texto = _texto_do_pdf(tmp_path / "ficha.pdf")
    assert paginas >= 2
    assert _esqueleto(f"Página 1 de {paginas}") in texto
    assert _esqueleto(f"Página {paginas} de {paginas}") in texto
    assert _esqueleto("Inativa") in texto  # a ficha mostra tudo, inclusive o que está inativo
    assert _esqueleto("financeiro@exemplo.com.br") in texto


def test_janela_de_impressao_salva_em_pdf(aplicacao, cenario, tmp_path):
    base, a, _ = cenario
    impressao = dados_para_pagamento([consultar(base.conexao, a)], None, QUANDO)
    janela = JanelaImpressao(None, impressao)
    janela.escolher_arquivo = lambda: str(tmp_path / "salvo")
    janela.salvar.click()
    assert (tmp_path / "salvo.pdf").stat().st_size > 1000
    assert janela.impresso
    assert "salvo.pdf" in janela.retorno.text()
