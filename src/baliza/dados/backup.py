"""Backups: cópia do arquivo de dados ao fechar, exportar e restaurar (RF22 a RF25).

O backup é uma cópia do próprio arquivo cifrado: abre com a mesma senha ou a mesma chave de
recuperação que valiam quando ele foi feito (RNF06). Nada sai do computador (RNF13).
"""

from __future__ import annotations

import os
import shutil
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from baliza.dados.banco import BaseDeDados

BACKUP_AUTOMATICO = "backup_automatico"
COPIAS = "backup_copias"
COPIAS_PADRAO = 7
COPIAS_MAXIMO = 60
PREFIXO = "baliza-"
EXTENSAO = ".baliza"
FORMATO_DATA = "%Y%m%d-%H%M%S"


@dataclass(frozen=True)
class Backup:
    caminho: Path
    quando: datetime
    tamanho: int

    @property
    def tamanho_legivel(self) -> str:
        if self.tamanho < 1024 * 1024:
            return f"{max(1, round(self.tamanho / 1024))} KB"
        return f"{self.tamanho / (1024 * 1024):.1f} MB".replace(".", ",")


def pasta_de_backups(caminho_dados: Path) -> Path:
    return Path(caminho_dados).parent / "backups"


def nome_do_backup(quando: datetime) -> str:
    return f"{PREFIXO}{quando.strftime(FORMATO_DATA)}{EXTENSAO}"


def _copiar(origem: Path, destino: Path) -> None:
    """Cópia atômica: um backup pela metade nunca fica com o nome final."""
    destino.parent.mkdir(parents=True, exist_ok=True)
    temporario = destino.with_name(destino.name + ".tmp")
    shutil.copyfile(origem, temporario)
    os.replace(temporario, destino)


def fazer_backup(caminho_dados: Path, pasta: Path, quando: datetime | None = None) -> Path:
    quando = (quando or datetime.now()).replace(microsecond=0)
    destino = Path(pasta) / nome_do_backup(quando)
    _copiar(Path(caminho_dados), destino)
    return destino


def listar_backups(pasta: Path) -> list[Backup]:
    """Mais novo primeiro. Só os arquivos com o nome que o Baliza dá aos backups."""
    pasta = Path(pasta)
    if not pasta.is_dir():
        return []
    backups = []
    for arquivo in pasta.glob(f"{PREFIXO}*{EXTENSAO}"):
        try:
            quando = datetime.strptime(arquivo.name[len(PREFIXO) : -len(EXTENSAO)], FORMATO_DATA)
        except ValueError:
            continue
        backups.append(Backup(arquivo, quando, arquivo.stat().st_size))
    return sorted(backups, key=lambda b: b.quando, reverse=True)


def manter_ultimas(pasta: Path, quantas: int) -> list[Path]:
    """RF23: fica só a quantidade escolhida; as mais antigas são apagadas."""
    sobra = listar_backups(pasta)[max(1, quantas) :]
    for backup in sobra:
        backup.caminho.unlink()
    return [b.caminho for b in sobra]


def copias_escolhidas(base: BaseDeDados) -> int:
    try:
        return min(COPIAS_MAXIMO, max(1, int(base.configuracao(COPIAS, str(COPIAS_PADRAO)))))
    except ValueError:
        return COPIAS_PADRAO


def automatico_ligado(base: BaseDeDados) -> bool:
    return base.configuracao(BACKUP_AUTOMATICO, "sim") == "sim"


def backup_ao_fechar(
    base: BaseDeDados, caminho_dados: Path, quando: datetime | None = None
) -> Path | None:
    """RF22: chamado depois de gravar os dados, quando o Baliza é fechado."""
    if not automatico_ligado(base):
        return None
    pasta = pasta_de_backups(caminho_dados)
    feito = fazer_backup(caminho_dados, pasta, quando)
    manter_ultimas(pasta, copias_escolhidas(base))
    return feito


def exportar(caminho_dados: Path, pasta_destino: Path, quando: datetime | None = None) -> Path:
    """RF24: uma cópia para outro lugar (pendrive, outro disco)."""
    return fazer_backup(caminho_dados, pasta_destino, quando)


def restaurar(
    arquivo_backup: Path,
    caminho_dados: Path,
    *,
    senha: str | None = None,
    chave: str | None = None,
    quando: datetime | None = None,
) -> BaseDeDados:
    """RF25: confere a senha ou a chave do backup antes de mexer nos dados atuais.

    Os dados atuais viram um backup ("antes de restaurar") e só então são substituídos.
    Senha ou chave errada levantam o erro do Cofre sem mudar nada.
    """
    caminho_dados = Path(caminho_dados)
    with tempfile.TemporaryDirectory() as pasta_temporaria:
        copia = Path(pasta_temporaria) / "conferencia.baliza"
        shutil.copyfile(arquivo_backup, copia)
        conferida = BaseDeDados.abrir(copia, senha=senha, chave=chave)  # migra se precisar
        conferida.conexao.close()
        if caminho_dados.exists():
            fazer_backup(caminho_dados, pasta_de_backups(caminho_dados), quando)
        _copiar(copia, caminho_dados)
    return BaseDeDados.abrir(caminho_dados, senha=senha, chave=chave)
