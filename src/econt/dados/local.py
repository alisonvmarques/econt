"""Onde o arquivo de dados fica no computador."""

import os
import shutil
import sys
from pathlib import Path

NOME_ARQUIVO = "dados.econt"

# Antes de novembro de 2026 o sistema se chamava Baliza e guardava os dados em outra pasta.
NOME_ANTERIOR = "Baliza"
ARQUIVO_ANTERIOR = "dados.baliza"
PREFIXO_BACKUP_ANTERIOR = "baliza-"
EXTENSAO_ANTERIOR = ".baliza"


def _pasta(nome: str) -> Path:
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
        return base / nome
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / nome
    base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return base / nome.lower()


def pasta_de_dados() -> Path:
    return _pasta("ECont")


def pasta_anterior() -> Path:
    return _pasta(NOME_ANTERIOR)


def caminho_padrao() -> Path:
    """O arquivo de dados. A variável ECONT_ARQUIVO permite usar outro (testes, pendrive)."""
    escolhido = os.environ.get("ECONT_ARQUIVO")
    return Path(escolhido) if escolhido else pasta_de_dados() / NOME_ARQUIVO


def trazer_dados_anteriores(origem: Path | None = None, destino: Path | None = None) -> bool:
    """Na primeira vez que o ECont abre, copia os dados e os backups gravados com o nome
    anterior do sistema. A pasta antiga fica como estava: nada é apagado ou movido.

    Devolve True se copiou. O arquivo é o mesmo, com a mesma senha e a mesma chave de
    recuperação; só muda de nome.
    """
    if destino is None:
        if os.environ.get("ECONT_ARQUIVO"):
            return False
        destino = pasta_de_dados()
    origem = origem or pasta_anterior()
    antigo = origem / ARQUIVO_ANTERIOR
    novo = destino / NOME_ARQUIVO
    if novo.exists() or not antigo.is_file():
        return False
    destino.mkdir(parents=True, exist_ok=True)
    backups_antigos = origem / "backups"
    if backups_antigos.is_dir():
        backups = destino / "backups"
        backups.mkdir(exist_ok=True)
        for arquivo in backups_antigos.glob(f"{PREFIXO_BACKUP_ANTERIOR}*{EXTENSAO_ANTERIOR}"):
            data = arquivo.name[len(PREFIXO_BACKUP_ANTERIOR) : -len(EXTENSAO_ANTERIOR)]
            alvo = backups / f"econt-{data}.econt"
            if not alvo.exists():
                shutil.copy2(arquivo, alvo)
    # O arquivo de dados por último: se algo falhar antes, a cópia é refeita na próxima vez.
    temporario = novo.with_name(novo.name + ".tmp")
    shutil.copy2(antigo, temporario)
    os.replace(temporario, novo)
    return True
