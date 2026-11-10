import pytest

from econt.dominio.documentos import (
    cnpj_valido,
    cpf_valido,
    formatar_cnpj,
    formatar_cpf,
    somente_caracteres,
)


@pytest.mark.parametrize(
    "cnpj",
    [
        "11.222.333/0001-81",
        "11222333000181",
        "12.ABC.345/01DE-35",  # exemplo oficial do CNPJ alfanumérico da Receita Federal
        "12abc34501de35",
    ],
)
def test_cnpj_valido(cnpj):
    assert cnpj_valido(cnpj)


@pytest.mark.parametrize(
    "cnpj",
    [
        "11.222.333/0001-80",
        "11.111.111/1111-11",
        "123",
        "12.ABC.345/01DE-3A",
        "",
        "AB.CDE.FGH/IJKL-MN",
    ],
)
def test_cnpj_invalido(cnpj):
    assert not cnpj_valido(cnpj)


def test_cpf():
    assert cpf_valido("529.982.247-25")
    assert not cpf_valido("529.982.247-24")
    assert not cpf_valido("111.111.111-11")
    assert not cpf_valido("123")


def test_formatacao():
    assert somente_caracteres(" 11.222.333/0001-81 ") == "11222333000181"
    assert formatar_cnpj("11222333000181") == "11.222.333/0001-81"
    assert formatar_cnpj("12abc34501de35") == "12.ABC.345/01DE-35"
    assert formatar_cpf("52998224725") == "529.982.247-25"


@pytest.mark.parametrize(
    "tipo, documento, mensagem",
    [
        ("pf", "", "Informe o CPF."),
        ("pf", "529.982.247-2", "O CPF tem 11 números; este tem 10."),
        ("pf", "529.982.247-24", "CPF inválido: confira os dois últimos dígitos."),
        ("pf", "529.98A.247-25", "O CPF tem só números."),
        ("pj", "11.222.333/0001", "O CNPJ tem 14 caracteres; este tem 12."),
        ("pj", "11.222.333/0001-80", "CNPJ inválido: confira os dois últimos dígitos."),
        ("pj", "12.ABC.345/01DE-3A", "Os dois últimos caracteres do CNPJ são números."),
    ],
)
def test_mensagem_clara_do_documento_errado(tipo, documento, mensagem):
    from econt.dominio.documentos import problema_do_documento

    assert problema_do_documento(tipo, documento) == mensagem


@pytest.mark.parametrize(
    "tipo, documento",
    [("pf", "529.982.247-25"), ("pj", "11.222.333/0001-81"), ("pj", "12.ABC.345/01DE-35")],
)
def test_documento_certo_nao_tem_mensagem(tipo, documento):
    from econt.dominio.documentos import problema_do_documento

    assert problema_do_documento(tipo, documento) is None
