"""RNF16: CNPJ, CPF, telefone e data se formatam enquanto se digita."""

import pytest
from PySide6.QtTest import QTest

from econt.dominio.formatos import (
    chave_pix_ao_digitar,
    cnpj_ao_digitar,
    cpf_ao_digitar,
    data_ao_digitar,
    documento_ao_digitar,
    telefone_ao_digitar,
)


@pytest.mark.parametrize(
    ("digitado", "esperado"),
    [
        ("", ""),
        ("11", "11"),
        ("112", "11.2"),
        ("11222333", "11.222.333"),
        ("112223330", "11.222.333/0"),
        ("1122233300018", "11.222.333/0001-8"),
        ("11222333000181", "11.222.333/0001-81"),
        ("11.222.333/0001-81", "11.222.333/0001-81"),
        ("112223330001819", "11.222.333/0001-81"),  # o que passa de 14 fica de fora
        ("12abc3456789", "12.ABC.345/6789"),  # CNPJ alfanumérico
    ],
)
def test_cnpj(digitado, esperado):
    assert cnpj_ao_digitar(digitado) == esperado


def test_cpf_e_documento_pelo_tipo():
    assert cpf_ao_digitar("5299") == "529.9"
    assert cpf_ao_digitar("52998224725") == "529.982.247-25"
    assert cpf_ao_digitar("abc") == "abc"
    assert documento_ao_digitar("pf", "52998224725") == "529.982.247-25"
    assert documento_ao_digitar("pj", "11222333000181") == "11.222.333/0001-81"


@pytest.mark.parametrize(
    ("digitado", "esperado"),
    [
        ("", ""),
        ("8", "(8"),
        ("81", "(81"),
        ("813", "(81) 3"),
        ("81333", "(81) 333"),
        ("813333000", "(81) 3333-000"),
        ("8133330000", "(81) 3333-0000"),
        ("81999990000", "(81) 99999-0000"),
        ("(81) 99999-0000", "(81) 99999-0000"),
        ("0800 123 4567", "0800 123 4567"),  # 0800 fica como veio
        ("+55 81 99999", "+55 81 99999"),
        ("3333-0000 ramal 2", "3333-0000 ramal 2"),
    ],
)
def test_telefone(digitado, esperado):
    assert telefone_ao_digitar(digitado) == esperado


@pytest.mark.parametrize(
    ("digitado", "esperado"),
    [
        ("", ""),
        ("2", "2"),
        ("25", "25"),
        ("251", "25/1"),
        ("2511", "25/11"),
        ("25112026", "25/11/2026"),
        ("251120261", "25/11/2026"),
        ("5/", "05"),
        ("5/1/2027", "05/01/2027"),
        ("25/11/2026", "25/11/2026"),
        ("hoje", "hoje"),
    ],
)
def test_data(digitado, esperado):
    assert data_ao_digitar(digitado) == esperado


def test_chave_pix_pelo_tipo():
    assert chave_pix_ao_digitar("cpf", "52998224725") == "529.982.247-25"
    assert chave_pix_ao_digitar("cnpj", "11222333000181") == "11.222.333/0001-81"
    assert chave_pix_ao_digitar("telefone", "81999990000") == "(81) 99999-0000"
    assert chave_pix_ao_digitar("email", "a@b.com") == "a@b.com"


def test_campo_formata_enquanto_digita_e_o_cursor_acompanha(aplicacao):
    from econt.interface.componentes import Campo, formatar_ao_digitar

    campo = Campo("CNPJ")
    formatar_ao_digitar(campo.caixa, cnpj_ao_digitar)
    campo.show()
    QTest.keyClicks(campo.caixa, "11222333000181")
    assert campo.valor() == "11.222.333/0001-81"
    assert campo.caixa.cursorPosition() == len(campo.valor())
    # Corrigir um número no meio: o cursor fica logo depois dele.
    campo.caixa.setCursorPosition(4)  # depois de "11.2"
    QTest.keyClicks(campo.caixa, "9")
    assert campo.valor() == "11.292.233/3000-18"
    assert campo.valor()[: campo.caixa.cursorPosition()] == "11.29"


def test_formularios_formatam_ao_digitar(aplicacao, tmp_path):
    from econt.dados.banco import BaseDeDados
    from econt.interface.fornecedores import PaginaFornecedores

    base = BaseDeDados.criar(tmp_path / "dados.econt", "fundo2026saude")[0]
    pagina = PaginaFornecedores(base)
    pagina.abrir_formulario(None)
    form = pagina.formulario
    QTest.keyClicks(form.documento.caixa, "11222333000181")
    QTest.keyClicks(form.telefone.caixa, "8133330000")
    assert form.documento.valor() == "11.222.333/0001-81"
    assert form.telefone.valor() == "(81) 3333-0000"
    form.tipo.definir("pf")
    form.documento.definir("")
    QTest.keyClicks(form.documento.caixa, "52998224725")
    assert form.documento.valor() == "529.982.247-25"
