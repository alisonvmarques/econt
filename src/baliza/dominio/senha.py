"""Regras da senha do Baliza (RNF07)."""

TAMANHO_MINIMO = 10


def problemas_da_senha(senha: str) -> list[str]:
    """Lista o que falta para a senha ser aceita. Lista vazia: senha aceita."""
    faltando = []
    if len(senha) < TAMANHO_MINIMO:
        faltando.append(f"pelo menos {TAMANHO_MINIMO} caracteres")
    if not any(c.isalpha() for c in senha):
        faltando.append("uma letra")
    if not any(c.isdigit() for c in senha):
        faltando.append("um número")
    return faltando


def mensagem_senha_fraca(faltando: list[str]) -> str:
    if len(faltando) == 1:
        return f"Senha fraca: falta {faltando[0]}."
    return "Senha fraca: falta " + ", ".join(faltando[:-1]) + f" e {faltando[-1]}."
