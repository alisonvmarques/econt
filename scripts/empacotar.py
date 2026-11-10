"""Gera o instalador do ECont para o sistema em que roda, e confere se ele abre (RNF10).

Uso, a partir da raiz do repositório, com o ECont e as ferramentas instalados
(pip install -e ".[empacotar]"):

    python scripts/empacotar.py            # gera o instalador em dist/
    python scripts/empacotar.py verificar  # instala ou abre o instalador gerado e confere

No Windows, o instalador é feito com o Inno Setup; no Linux, o AppImage precisa do
appimagetool (caminho na variável APPIMAGETOOL). O GitHub Actions faz tudo isso sozinho
quando uma versão é criada; veja .github/workflows/instaladores.yml.
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DIST = RAIZ / "dist"
OBRA = RAIZ / "build"
ICONE_SVG = RAIZ / "src" / "econt" / "interface" / "icone.svg"
EMPACOTAMENTO = RAIZ / "empacotamento"


def versao() -> str:
    from econt import __version__

    return __version__


def sistema() -> str:
    return {"Windows": "windows", "Darwin": "macos"}.get(platform.system(), "linux")


def rodar(*comando: str | Path, **opcoes) -> None:
    print("$", " ".join(str(c) for c in comando), flush=True)
    subprocess.run([str(c) for c in comando], check=True, **opcoes)


def gerar_icones() -> dict[str, Path]:
    """PNG de 1024 px desenhado pelo Qt a partir do SVG; .ico e .icns pelo Pillow."""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PIL import Image
    from PySide6.QtGui import QIcon
    from PySide6.QtWidgets import QApplication

    pasta = OBRA / "icones"
    pasta.mkdir(parents=True, exist_ok=True)
    QApplication.instance() or QApplication([])
    png = pasta / "econt.png"
    QIcon(str(ICONE_SVG)).pixmap(1024, 1024).save(str(png))
    imagem = Image.open(png)
    ico = pasta / "econt.ico"
    imagem.save(
        ico, sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    )
    icns = pasta / "econt.icns"
    imagem.save(icns)
    return {"png": png, "ico": ico, "icns": icns}


def pyinstaller(icones: dict[str, Path]) -> None:
    """Uma pasta com o programa e tudo o que ele usa (lista de bancos, ícones do tema)."""
    icone = icones["ico"] if sistema() == "windows" else icones["icns"]
    opcoes = [
        "--noconfirm",
        "--clean",
        "--name",
        "ECont",
        "--windowed",
        "--onedir",
        "--collect-data",
        "econt",
        "--icon",
        icone,
        "--distpath",
        DIST,
        "--workpath",
        OBRA / "pyinstaller",
        "--specpath",
        OBRA,
    ]
    if sistema() == "macos":
        opcoes += ["--osx-bundle-identifier", "io.github.alisonvmarques.econt"]
    rodar(sys.executable, "-m", "PyInstaller", *opcoes, RAIZ / "src" / "econt" / "__main__.py")


def instalador_windows(icones: dict[str, Path]) -> Path:
    iscc = shutil.which("iscc") or r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
    rodar(
        iscc,
        f"/DVersao={versao()}",
        f"/DOrigem={DIST / 'ECont'}",
        f"/DSaida={DIST}",
        f"/DIcone={icones['ico']}",
        EMPACOTAMENTO / "windows" / "econt.iss",
    )
    return DIST / f"ECont-{versao()}-Windows-instalador.exe"


def instalador_macos() -> Path:
    """Imagem .dmg com o ECont.app e o atalho para Aplicativos, para arrastar."""
    palco = OBRA / "dmg"
    shutil.rmtree(palco, ignore_errors=True)
    palco.mkdir(parents=True)
    shutil.copytree(DIST / "ECont.app", palco / "ECont.app", symlinks=True)
    (palco / "Aplicativos").symlink_to("/Applications")
    saida = DIST / f"ECont-{versao()}-macOS.dmg"
    saida.unlink(missing_ok=True)
    rodar(
        "hdiutil",
        "create",
        "-volname",
        "ECont",
        "-srcfolder",
        palco,
        "-ov",
        "-format",
        "UDZO",
        saida,
    )
    return saida


def instalador_linux(icones: dict[str, Path]) -> Path:
    """AppImage: um arquivo só, que roda sem instalar."""
    appdir = OBRA / "ECont.AppDir"
    shutil.rmtree(appdir, ignore_errors=True)
    (appdir / "usr" / "lib").mkdir(parents=True)
    shutil.copytree(DIST / "ECont", appdir / "usr" / "lib" / "econt", symlinks=True)
    shutil.copy(EMPACOTAMENTO / "linux" / "AppRun", appdir / "AppRun")
    (appdir / "AppRun").chmod(0o755)
    shutil.copy(EMPACOTAMENTO / "linux" / "econt.desktop", appdir / "econt.desktop")
    shutil.copy(icones["png"], appdir / "econt.png")
    ferramenta = os.environ.get("APPIMAGETOOL", "appimagetool")
    saida = DIST / f"ECont-{versao()}-Linux-x86_64.AppImage"
    ambiente = {**os.environ, "ARCH": "x86_64", "APPIMAGE_EXTRACT_AND_RUN": "1"}
    rodar(ferramenta, appdir, saida, env=ambiente)
    return saida


def empacotar() -> Path:
    icones = gerar_icones()
    pyinstaller(icones)
    if sistema() == "windows":
        return instalador_windows(icones)
    if sistema() == "macos":
        return instalador_macos()
    return instalador_linux(icones)


def verificar() -> int:
    """Instala (Windows), monta (macOS) ou roda (Linux) o instalador e abre o ECont com
    --verificar. Imprime o relatório e devolve o código de saída do programa."""
    ambiente = {**os.environ, "QT_QPA_PLATFORM": "offscreen"}
    relatorio = Path(tempfile.mkdtemp()) / "relatorio.txt"
    montado = None
    try:
        if sistema() == "windows":
            pasta = Path(tempfile.mkdtemp()) / "ECont"
            rodar(
                DIST / f"ECont-{versao()}-Windows-instalador.exe",
                "/VERYSILENT",
                "/SUPPRESSMSGBOXES",
                "/NORESTART",
                "/CURRENTUSER",
                f"/DIR={pasta}",
            )
            programa = pasta / "ECont.exe"
        elif sistema() == "macos":
            montado = Path(tempfile.mkdtemp())
            rodar(
                "hdiutil",
                "attach",
                DIST / f"ECont-{versao()}-macOS.dmg",
                "-mountpoint",
                montado,
                "-nobrowse",
            )
            programa = montado / "ECont.app" / "Contents" / "MacOS" / "ECont"
        else:
            programa = DIST / f"ECont-{versao()}-Linux-x86_64.AppImage"
            ambiente["APPIMAGE_EXTRACT_AND_RUN"] = "1"
        resultado = subprocess.run(
            [str(programa), "--verificar", str(relatorio)], env=ambiente, timeout=180
        )
    finally:
        if montado:
            subprocess.run(["hdiutil", "detach", str(montado)], check=False)
    print(relatorio.read_text(encoding="utf-8") if relatorio.exists() else "sem relatório")
    return resultado.returncode if relatorio.exists() else 1


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "verificar":
        sys.exit(verificar())
    print(f"Instalador gerado: {empacotar()}")
