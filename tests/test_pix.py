import pytest

from econt.dominio.pix import ChaveInvalida, formatar_chave, normalizar_chave


@pytest.mark.parametrize(
    "tipo, chave, guardada",
    [
        ("cpf", "529.982.247-25", "52998224725"),
        ("cnpj", "12.ABC.345/01DE-35", "12ABC34501DE35"),
        ("email", "Financeiro@Exemplo.com.br", "financeiro@exemplo.com.br"),
        ("telefone", "(81) 99999-0000", "+5581999990000"),
        ("telefone", "+55 81 3000-0000", "+558130000000"),
        (
            "aleatoria",
            "1A2B3C4D-1A2B-4A2B-8A2B-1A2B3C4D5E6F",
            "1a2b3c4d-1a2b-4a2b-8a2b-1a2b3c4d5e6f",
        ),
    ],
)
def test_chave_no_formato_do_tipo(tipo, chave, guardada):
    assert normalizar_chave(tipo, chave) == guardada


@pytest.mark.parametrize(
    "tipo, chave, mensagem",
    [
        ("cpf", "529.982.247-24", "CPF inválido"),
        ("cnpj", "11.222.333/0001-80", "CNPJ inválido"),
        ("email", "financeiro@", "E-mail inválido"),
        ("email", "financeiro exemplo.com", "E-mail inválido"),
        ("telefone", "99999-0000", "DDD"),
        ("telefone", "+1 555 123 4567", "Brasil"),
        ("aleatoria", "123", "36 caracteres"),
        ("cpf", "", "Informe a chave"),
        ("outro", "x", "tipo"),
    ],
)
def test_chave_fora_do_formato_e_recusada(tipo, chave, mensagem):
    with pytest.raises(ChaveInvalida, match=mensagem):
        normalizar_chave(tipo, chave)


def test_chave_formatada_para_mostrar():
    assert formatar_chave("telefone", "+5581999990000") == "(81) 99999-0000"
    assert formatar_chave("telefone", "+558130000000") == "(81) 3000-0000"
    assert formatar_chave("cnpj", "11222333000181") == "11.222.333/0001-81"
    assert formatar_chave("email", "a@b.com") == "a@b.com"
