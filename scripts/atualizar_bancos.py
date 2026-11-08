"""Gera src/baliza/dados/recursos/bancos.csv a partir da lista oficial do Banco Central.

Uso:
    python scripts/atualizar_bancos.py caminho/para/ParticipantesSTR.csv

Passo a passo completo em docs/atualizar-lista-de-bancos.md.
"""

import csv
import sys
from pathlib import Path

DESTINO = Path(__file__).resolve().parent.parent / "src/baliza/dados/recursos/bancos.csv"


def converter(origem: Path) -> list[tuple[str, str, str]]:
    with open(origem, encoding="utf-8-sig", newline="") as arquivo:
        linhas = list(csv.DictReader(arquivo))
    bancos = {}
    for linha in linhas:
        codigo = (linha.get("Número_Código") or "").strip()
        if not codigo.isdigit() or int(codigo) == 0:
            continue  # sem código COMPE: não recebe transferências por agência e conta
        codigo = codigo.zfill(3)
        bancos[codigo] = (codigo, linha["ISPB"].strip(), linha["Nome_Extenso"].strip())
    return sorted(bancos.values())


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit("Uso: python scripts/atualizar_bancos.py ParticipantesSTR.csv")
    bancos = converter(Path(sys.argv[1]))
    with open(DESTINO, "w", encoding="utf-8", newline="") as arquivo:
        escritor = csv.writer(arquivo)
        escritor.writerow(["codigo", "ispb", "nome"])
        escritor.writerows(bancos)
    print(f"{len(bancos)} bancos gravados em {DESTINO}")


if __name__ == "__main__":
    main()
