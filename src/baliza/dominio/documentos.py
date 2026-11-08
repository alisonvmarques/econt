"""CPF e CNPJ (RN01), incluindo o CNPJ alfanumérico da Receita Federal."""

PESOS_CNPJ_1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
PESOS_CNPJ_2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]


def somente_caracteres(documento: str) -> str:
    """Tira pontos, barras, traços e espaços, e passa as letras para maiúsculas."""
    return "".join(c for c in documento.upper() if c.isalnum())


def _digito(valores: list[int], pesos: list[int]) -> int:
    resto = sum(v * p for v, p in zip(valores, pesos, strict=True)) % 11
    return 0 if resto < 2 else 11 - resto


def cnpj_valido(cnpj: str) -> bool:
    """Aceita o CNPJ numérico e o alfanumérico (12 primeiros podem ter letras)."""
    c = somente_caracteres(cnpj)
    if len(c) != 14 or not c[12:].isdigit():
        return False
    if not all(ch.isdigit() or "A" <= ch <= "Z" for ch in c[:12]):
        return False
    if len(set(c)) == 1:
        return False
    valores = [ord(ch) - 48 for ch in c]
    d1 = _digito(valores[:12], PESOS_CNPJ_1)
    d2 = _digito(valores[:12] + [d1], PESOS_CNPJ_2)
    return c[12:] == f"{d1}{d2}"


def cpf_valido(cpf: str) -> bool:
    c = somente_caracteres(cpf)
    if len(c) != 11 or not c.isdigit() or len(set(c)) == 1:
        return False
    numeros = [int(n) for n in c]
    for posicao in (9, 10):
        soma = sum(n * p for n, p in zip(numeros[:posicao], range(posicao + 1, 1, -1), strict=True))
        if (soma * 10 % 11) % 10 != numeros[posicao]:
            return False
    return True


def formatar_cnpj(cnpj: str) -> str:
    c = somente_caracteres(cnpj)
    if len(c) != 14:
        return cnpj
    return f"{c[:2]}.{c[2:5]}.{c[5:8]}/{c[8:12]}-{c[12:]}"


def formatar_cpf(cpf: str) -> str:
    c = somente_caracteres(cpf)
    if len(c) != 11:
        return cpf
    return f"{c[:3]}.{c[3:6]}.{c[6:9]}-{c[9:]}"


TIPOS_DE_PESSOA = {"pj": "Pessoa jurídica", "pf": "Pessoa física"}
NOME_DO_DOCUMENTO = {"pj": "CNPJ", "pf": "CPF"}


def problema_do_documento(tipo: str, documento: str) -> str | None:
    """Mensagem clara do que está errado no CPF ou CNPJ, ou None quando está certo (RN01)."""
    nome = NOME_DO_DOCUMENTO[tipo]
    c = somente_caracteres(documento)
    if not c:
        return f"Informe o {nome}."
    if tipo == "pf":
        if not c.isdigit():
            return "O CPF tem só números."
        if len(c) != 11:
            return f"O CPF tem 11 números; este tem {len(c)}."
        return None if cpf_valido(c) else "CPF inválido: confira os dois últimos dígitos."
    if len(c) != 14:
        return f"O CNPJ tem 14 caracteres; este tem {len(c)}."
    if not c[12:].isdigit():
        return "Os dois últimos caracteres do CNPJ são números."
    return None if cnpj_valido(c) else "CNPJ inválido: confira os dois últimos dígitos."


def formatar_documento(tipo: str, documento: str) -> str:
    return formatar_cpf(documento) if tipo == "pf" else formatar_cnpj(documento)
