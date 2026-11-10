from datetime import datetime

import pytest
from PySide6.QtPdf import QPdfDocument

from econt.dados.banco import BaseDeDados
from econt.dados.consulta import consultar
from econt.dados.contas import DadosConta, cadastrar_conta
from econt.dados.entidade import Entidade, obter_entidade, salvar_entidade
from econt.dados.fornecedores import (
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
from econt.dados.marcacoes import itens_do_fornecedor, marcar_todas
from econt.interface.impressao import JanelaImpressao, salvar_pdf_impressao
from econt.interface.impressoes import dados_para_pagamento, ficha_completa

SENHA = "fundo2026saude"
QUANDO = datetime(2026, 11, 8, 19, 5)


@pytest.fixture
def cenario(tmp_path):
    base = BaseDeDados.criar(tmp_path / "dados.econt", SENHA)[0]
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


def _paginas_do_pdf(caminho) -> int:
    pdf = QPdfDocument(None)
    pdf.load(str(caminho))
    paginas = pdf.pageCount()
    pdf.close()
    return paginas


@pytest.fixture
def desenhado(monkeypatch):
    """Guarda o HTML de tudo o que é desenhado na folha (blocos, rodapés, "corte aqui").

    O conteúdo é conferido aqui, antes de virar PDF: ler o texto de volta de um PDF depende
    do sistema (no Windows a leitura vem vazia, no macOS alguns números vêm trocados).
    """
    from econt.interface import impressao

    textos = []
    original = impressao._documento_no

    def guardar(dispositivo, html, logo, largura):
        textos.append(html)
        return original(dispositivo, html, logo, largura)

    monkeypatch.setattr(impressao, "_documento_no", guardar)
    return textos


def test_folha_completa_com_dois_fornecedores_e_linha_de_corte(
    aplicacao, cenario, tmp_path, desenhado
):
    base, a, b = cenario
    c = base.conexao
    impressao = dados_para_pagamento([consultar(c, a), consultar(c, b)], obter_entidade(c), QUANDO)
    salvar_pdf_impressao(impressao, str(tmp_path / "folha.pdf"))
    assert _paginas_do_pdf(tmp_path / "folha.pdf") == 1
    tudo = "\n".join(desenhado)
    assert "Distribuidora Exemplo de Materiais Ltda" in tudo
    assert "Maria Exemplo da Silva" in tudo
    assert "corte aqui" in tudo
    assert tudo.count("Emitido pelo ECont em 08/11/2026 às 19:05") == 2
    assert tudo.count("Fundo de Saúde Exemplo") == 2


def test_meia_folha_mostra_onde_esta_cadastrada_e_so_o_que_esta_ativo(
    aplicacao, cenario, tmp_path, desenhado
):
    base, a, _ = cenario
    c = base.conexao
    salvar_pdf_impressao(
        dados_para_pagamento([consultar(c, a)], obter_entidade(c), QUANDO),
        str(tmp_path / "meia.pdf"),
    )
    tudo = "\n".join(desenhado)
    assert "001 · Ag. 1234-5 · C/C 98765-4" in tudo
    assert "Conta Movimento" in tudo
    assert "Nenhuma: não usar para pagar" in tudo
    assert "33333-1" not in tudo  # conta inativa não sai na meia folha (RNF11)


def test_meia_folha_aceita_um_ou_dois(aplicacao, cenario):
    base, a, b = cenario
    resultados = [consultar(base.conexao, a)] * 3
    with pytest.raises(ValueError):
        dados_para_pagamento(resultados, None, QUANDO)


def test_ficha_completa_quebra_pagina_e_numera(aplicacao, cenario, tmp_path, desenhado):
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
    paginas = _paginas_do_pdf(tmp_path / "ficha.pdf")
    assert paginas >= 2
    tudo = "\n".join(desenhado)
    assert f"Página 1 de {paginas}" in tudo
    assert f"Página {paginas} de {paginas}" in tudo
    assert "Inativa" in tudo  # a ficha mostra tudo, inclusive o que está inativo
    assert "financeiro@exemplo.com.br" in tudo


def test_janela_de_impressao_salva_em_pdf(aplicacao, cenario, tmp_path):
    base, a, _ = cenario
    impressao = dados_para_pagamento([consultar(base.conexao, a)], None, QUANDO)
    janela = JanelaImpressao(None, impressao)
    janela.escolher_arquivo = lambda: str(tmp_path / "salvo")
    janela.salvar.click()
    assert (tmp_path / "salvo.pdf").stat().st_size > 1000
    assert janela.impresso
    assert "salvo.pdf" in janela.retorno.text()
