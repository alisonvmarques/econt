from econt.dominio.senha import mensagem_senha_fraca, problemas_da_senha


def test_senha_forte_e_aceita():
    assert problemas_da_senha("fundo2026saude") == []


def test_senha_fraca_diz_o_que_falta():
    assert problemas_da_senha("abc") == ["pelo menos 10 caracteres", "um número"]
    assert problemas_da_senha("1234567890") == ["uma letra"]
    assert mensagem_senha_fraca(["uma letra"]) == "Senha fraca: falta uma letra."
    assert (
        mensagem_senha_fraca(["pelo menos 10 caracteres", "um número"])
        == "Senha fraca: falta pelo menos 10 caracteres e um número."
    )
