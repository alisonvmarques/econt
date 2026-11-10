import time

import pytest

from econt.dados.banco import BaseDeDados
from econt.dados.consulta import FornecedorInativo, buscar, consultar
from econt.dados.contas import DadosConta, cadastrar_conta, definir_ativa
from econt.dados.fornecedores import (
    DadosContaFornecedor,
    DadosFornecedor,
    cadastrar_fornecedor,
    definir_fornecedor_ativo,
    definir_item_ativo,
    salvar_chave_pix,
    salvar_conta_fornecedor,
)
from econt.dados.marcacoes import definir_marcacao, itens_do_fornecedor
from econt.dominio.documentos import formatar_cnpj
from econt.dominio.texto import encontrar, normalizar

SENHA = "fundo2026saude"


@pytest.fixture
def base(tmp_path):
    return BaseDeDados.criar(tmp_path / "dados.econt", SENHA)[0]


def test_normalizar_tira_acentos_e_maiusculas_sem_mudar_o_tamanho():
    assert normalizar("Laboratório FICTÍCIO Ação") == "laboratorio ficticio acao"
    assert len(normalizar("Ç ã ü")) == 5
    assert encontrar("Laboratório Fictício", "FICTICIO") == (12, 20)
    assert encontrar("Laboratório", "x") is None


def test_busca_por_nome_fantasia_e_documento(base):
    c = base.conexao
    cadastrar_fornecedor(
        c,
        DadosFornecedor(
            "pj",
            "11.222.333/0001-81",
            "Distribuidora Exemplo de Materiais Ltda",
            "Exemplo Materiais",
        ),
    )
    cadastrar_fornecedor(
        c, DadosFornecedor("pj", "12.ABC.345/01DE-35", "Laboratório Fictício Análises S.A.")
    )
    cadastrar_fornecedor(c, DadosFornecedor("pf", "529.982.247-25", "Maria Exemplo da Silva"))
    assert [e.fornecedor.razao_social for e in buscar(c, "LABORATORIO ficticio")] == [
        "Laboratório Fictício Análises S.A."
    ]
    assert [e.campo for e in buscar(c, "exemplo materiais")] == ["nome_fantasia"]
    assert [e.campo for e in buscar(c, "11.222")] == ["documento"]
    assert [e.campo for e in buscar(c, "12abc")] == ["documento"]
    assert buscar(c, "   ") == []
    # quem começa com o termo vem primeiro
    ordem = [e.fornecedor.razao_social for e in buscar(c, "ma")]
    assert ordem[0] == "Maria Exemplo da Silva"


def test_inativo_nao_aparece_na_consulta(base):
    c = base.conexao
    f = cadastrar_fornecedor(c, DadosFornecedor("pf", "529.982.247-25", "Maria Exemplo da Silva"))
    definir_fornecedor_ativo(c, f, False)
    assert buscar(c, "maria") == []
    with pytest.raises(FornecedorInativo):
        consultar(c, f)


def test_resultado_mostra_onde_cada_uma_esta_cadastrada(base):
    c = base.conexao
    movimento = cadastrar_conta(c, DadosConta("Conta Movimento", "001", "1234-5", "55555-0"))
    cadastrar_conta(c, DadosConta("Conta Saúde", "104", "0456", "77777-1"))
    f = cadastrar_fornecedor(c, DadosFornecedor("pj", "11.222.333/0001-81", "Distribuidora"))
    salvar_conta_fornecedor(c, f, DadosContaFornecedor("001", "1234-5", "98765-4"))
    salvar_chave_pix(c, f, "email", "financeiro@exemplo.com.br")
    salvar_conta_fornecedor(c, f, DadosContaFornecedor("237", "0101", "33333-1"))
    itens = itens_do_fornecedor(c, f)
    conta, inativa = itens[0], itens[1]
    definir_item_ativo(c, "conta_fornecedor", inativa.id, False)
    definir_marcacao(c, conta, movimento, True)
    resultado = consultar(c, f)
    assert [x.descricao for x in resultado.contas_entidade] == ["Conta Movimento", "Conta Saúde"]
    assert [(x.item.nome, x.item.dados) for x in resultado.cadastros] == [
        ("Conta corrente", "001 · Ag. 1234-5 · C/C 98765-4"),
        ("Pix · E-mail", "financeiro@exemplo.com.br"),
    ]
    assert resultado.cadastrada(resultado.cadastros[0], resultado.contas_entidade[0])
    assert not resultado.cadastrada(resultado.cadastros[0], resultado.contas_entidade[1])
    assert [x.item.dados for x in resultado.sem_cadastro] == ["financeiro@exemplo.com.br"]
    definir_ativa(c, movimento, False)
    assert [x.item.dados for x in consultar(c, f).sem_cadastro] == [
        "001 · Ag. 1234-5 · C/C 98765-4",
        "financeiro@exemplo.com.br",
    ]


def test_busca_em_menos_de_um_segundo_com_500_fornecedores(base):
    """RNF02."""
    c = base.conexao
    for numero in range(500):
        raiz = f"{numero:08d}0001"
        cnpj = _cnpj_valido(raiz)
        cadastrar_fornecedor(
            c, DadosFornecedor("pj", cnpj, f"Fornecedor Fictício {numero:03d} Ltda")
        )
    inicio = time.perf_counter()
    encontrados = buscar(c, "ficticio 4")
    decorrido = time.perf_counter() - inicio
    assert len(encontrados) == 100
    assert decorrido < 1.0
    inicio = time.perf_counter()
    consultar(c, encontrados[0].fornecedor.id)
    assert time.perf_counter() - inicio < 1.0


def _cnpj_valido(raiz: str) -> str:
    from econt.dominio.documentos import PESOS_CNPJ_1, PESOS_CNPJ_2, _digito

    valores = [int(n) for n in raiz]
    d1 = _digito(valores, PESOS_CNPJ_1)
    d2 = _digito(valores + [d1], PESOS_CNPJ_2)
    return formatar_cnpj(f"{raiz}{d1}{d2}")
