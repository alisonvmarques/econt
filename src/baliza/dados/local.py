"""Onde o arquivo de dados fica no computador."""

import os
import sys
from pathlib import Path

NOME_ARQUIVO = "dados.baliza"


def pasta_de_dados() -> Path:
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
        return base / "Baliza"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "Baliza"
    base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return base / "baliza"


def caminho_padrao() -> Path:
    """O arquivo de dados. A variável BALIZA_ARQUIVO permite usar outro (testes, pendrive)."""
    escolhido = os.environ.get("BALIZA_ARQUIVO")
    return Path(escolhido) if escolhido else pasta_de_dados() / NOME_ARQUIVO
