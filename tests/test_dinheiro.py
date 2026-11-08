import pytest

from baliza.dominio.dinheiro import ValorInvalido, formatar_reais, ler_reais


@pytest.mark.parametrize(
    "texto, centavos",
    [
        ("R$ 25.000,00", 2_500_000),
        ("25000", 2_500_000),
        ("25.000", 2_500_000),
        ("25000,5", 2_500_050),
        ("0,99", 99),
        ("1.234.567,89", 123_456_789),
    ],
)
def test_le_valores_escritos_como_no_brasil(texto, centavos):
    assert ler_reais(texto) == centavos


@pytest.mark.parametrize("texto", ["", "abc", "25,000,00", "25.00", "10,999", "-5", "1.2345"])
def test_recusa_valores_mal_escritos(texto):
    with pytest.raises(ValorInvalido):
        ler_reais(texto)


def test_formata_em_reais():
    assert formatar_reais(1_000_000) == "R$ 10.000,00"
    assert formatar_reais(5) == "R$ 0,05"
    assert formatar_reais(123_456_789) == "R$ 1.234.567,89"
